##  Copyright 2024 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved.
##
##  For more Information on orm see the README file.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this program; if not, write to the Free Software
##  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##
##  I have added a copy of the GPL in the file LICENSE

import sys, os, os.path as op, re, runpy, inspect, threading, glob, subprocess
import urllib.parse, shutil, psycopg2.pool
from wsgiref.handlers import format_date_time

import flask
from werkzeug.exceptions import Unauthorized

from . import config, resource_path
from . import skinning
skin = skinning.Skin(config["WWW_PATH"])
from .db_sessions import DbSessionInterface

# Es ist zwar offensichtlich, was hier passiert, aber ich schreibe trotzdem
# mal einen Kommentar untendrunter.
from ll.xist import xsc
xsc.Node.__html__ = xsc.Node.string
# Chameleon benutzt bei Objekten, die eine __html__() methode haben,
# obj.__html__() Statt str(obj), was ja dann zu obj.__str__() wird.
# xsc.Node.__str__() liefert aber den *textlichen Inhalt* der Knoten zurück,
# nicht die HTML-Repräsentation, die ich gerne hätte. Das macht aber
# Node.string(). Damit ich nicht Node.string() immer irgendwo aufrufen muss,
# sondern einfach meine Funktionen in den Page Templates verwenden möchte,
# hier dieser kleine Kunstgriff.
# Die __html__()-Funktion ist dokumentiert:
# https://chameleon.readthedocs.io/en/latest/reference.html
#
# So könnte man da noch eingreifen:
#def xsc__html__(self):
#    return self.string()
#xsc.Node.__html__ = xsc__html__
#

# These are resources available to the python code but not to remote web
# clients.
module_cache = {}
module_load_lock = threading.Lock()

def create_app(test_config=None):
    from . import db
    from .utils import call_from_request, selected_elkg

    from . import authentication

    # create and configure the app
    app = flask.Flask(__name__, instance_relative_config=True)

    app.config.from_pyfile(os.getenv("APPLICATION_SETTINGS"), silent=False)

    from . import authentication_blueprint
    app.register_blueprint(authentication_blueprint.bp)

    app.session_interface = DbSessionInterface()

    app.db_connection_pool = psycopg2.pool.ThreadedConnectionPool(
        5, 50, **app.config["DATASOURCE"])

    @app.before_request
    def get_db_conn():
        flask.g.dbconn = app.db_connection_pool.getconn()

    @app.teardown_request
    def put_db_conn(request):
        flask.g.dbconn.rollback()
        app.db_connection_pool.putconn(flask.g.dbconn)

        if getattr(flask.g, "session_dbconn", None) is not None:
            flask.g.session_dbconn.rollback()
            app.db_connection_pool.putconn(flask.g.session_dbconn)


    # This is the default action that makes page template (.html) files
    # work in this app.
    template_path_re = re.compile("([a-z0-9][/a-z0-9_]*)\.([a-z]{2,3})")

    @app.route("/www/<path:template_path>", methods=['GET', 'POST'])
    def html_files(template_path):
        if ".." in template_path:
            raise ValueError(template_path)

        if not skin.resource_exists(template_path):
            found = False
            parts = template_path.split("/")
            filename = parts[-1]
            if filename == "index.py" and len(parts) > 1:
                parts[-1] = parts[-2]
                newpath = "/".join(parts)
                if skin.resource_exists(newpath + ".py"):
                    template_path = newpath + ".py"
                    found = True
                elif skin.resource_exists(newpath + ".html"):
                    template_path = newpath + ".html"
                    found = True

            if not found:
                d = f"{skin.resource_path(template_path)} not found."
                return flask.abort(404, description=d)

        if template_path.endswith(".html"):
            # HTML files are static.
            try:
                template = skin.load_template(template_path)
            except ValueError:
                err = f"{template_path} not found by loader."
                flask.abort( 404, description=err)

            response = flask.Response(template())
            if not app.debug:
                response.headers["Cache-Control"] = "max-age=604800"
                response.headers["Last-Modified"] = format_date_time(
                    skinning.startup_time)
            return response
        elif template_path.endswith(".py"):
            match = template_path_re.match(template_path)
            if match is None:
                raise ValueError(f"Illegal template name {template_path}.")
            else:
                py_path = skin.resource_path(template_path)
                # Is there a default template?
                # A .pt file with the same name at the same
                # location?
                pt_path = template_path[:-3] + ".pt"
                if skin.resource_exists(pt_path):
                    template = skin.load_template(pt_path)
                else:
                    template = None

                module_name, suffix = match.groups()

                with module_load_lock:
                    if py_path in module_cache:
                        module = module_cache[py_path]
                    else:
                        module = runpy.run_path(
                            py_path, run_name=module_name)
                        if not app.debug:
                            module_cache[py_path] = module

                function_name = module_name.rsplit("/", 1)[-1]
                if function_name in module:
                    function = module[function_name]
                elif "main" in module:
                    function = module["main"]
                else:
                    raise ValueError(f"No function in {module_name}")

                if inspect.isclass(function):
                    function = function()

                if template is None:
                    return call_from_request(function)
                else:
                    return call_from_request(function, template)
        else:
            raise ValueError(template_path)

    scss_cache = {}

    @app.route("/scss/<path:template_path>")
    def compile_scss(template_path):
        if template_path in scss_cache:
            result = scss_cache[template_path]
        else:
            rp = skin.resource_path(template_path)

            sassc = shutil.which("sassc")

            if app.debug:
                style = "expanded"
            else:
                style = "compressed"

            cmd = [sassc, "--style", style, rp]

            result = subprocess.run(
                cmd,
                capture_output=True, encoding="utf-8",
                check=True)

            result = result.stdout

            if not app.debug:
                scss_cache[template_path] = result

        response = flask.Response(result)
        response.headers["Content-Type"] = "text/css; charset=UTF-8"

        if app.debug:
            response.headers["Pragma"] = "no-cache"
        else:
            response.headers["Cache-Control"] = "max-age=6048000" # 10 weeks

        return response

    @app.errorhandler(Unauthorized)
    def redirect_to_login(exception):
        redirect_to = b"%s?%s" % ( flask.request.path.encode("utf-8"),
                                   flask.request.query_string, )
        return authentication_blueprint.login(
            redirect_to=redirect_to,
            description=exception.description,
            alert_class="danger")

    return app
