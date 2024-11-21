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

import sys, os, os.path as op, re, runpy, inspect, threading, json
import urllib.parse, psycopg2.pool
from wsgiref.handlers import format_date_time
from pathlib import Path

from sqlclasses import sql

import flask
from werkzeug.exceptions import Unauthorized

from . import config
from . import skinning
from . import controllers

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
    from . import config
    from . import db, authentication
    from .utils import call_from_request, rget

    # create and configure the app
    app = flask.Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(config)

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

    www_root = Path(config["WWW_PATH"])
    skin = skinning.Skin(config["WWW_PATH"])
    @app.before_request
    def make_skin():
        flask.g.skin = skin

    from . import markdown
    app.add_url_rule("/markdown/<path:infile_path>",
                     view_func=markdown.view_func)

    from . import authentication_blueprint
    app.register_blueprint(authentication_blueprint.bp)

    from .scss import compile_scss
    app.add_url_rule("/scss/<path:template_path>",
                     view_func=compile_scss)

    from .archive import archive_cgi
    app.add_url_rule("/archive.cgi", view_func=archive_cgi)

    from .model.congress import Congresses, Booking
    congresses = Congresses()

    @app.before_request
    def set_congresses():
        flask.g.congresses = congresses

    @app.route("/congress/<path:congress_path>")
    def congress_view(congress_path):
        congress_path = Path(congress_path)
        if congress_path.name == "index.md":
            congress_path = congress_path.parent
        congress = congresses.by_path(congress_path)
        if congress is None:
            return flask.abort(404)

        key = rget("key", None)
        if key:
            booking = Booking.select_one(congress.where(
                "slug = ", sql.string_literal(key)))
            error_message = "Ungültige Registrierungs-Mail!"
        else:
            booking = None
            error_message = None

        flask.g.congress = congress
        template = skin.load_template("skin/jugendkongress/congress_view.pt")
        return template(congress=congress,
                        booking=booking,
                        error_message=error_message)

    @app.route("/booking/<int:year>/<command>", methods=("POST",))
    def booking(year, command):
        congress = congresses.by_year(year)

        match command:
            case "create":
                ret = controllers.create_booking(congress)
            case "modify":
                ret = controllers.modify_booking(congress)
            case "resend":
                ret = controllers.resend_welcome(congress)
            case _:
                return flask.abort(404)

        response = flask.make_response(json.dumps(ret), 200)
        response.headers["Content-Type"] = "application/json"
        return response


    @app.route("/root")
    def root():
        # Forward the visitor to the youngest Kongress folder.
        return flask.redirect(congresses.current.href)

    @app.errorhandler(Unauthorized)
    def redirect_to_login(exception):
        redirect_to = b"%s?%s" % ( flask.request.path.encode("utf-8"),
                                   flask.request.query_string, )
        return authentication_blueprint.login(
            redirect_to=redirect_to,
            description=exception.description,
            alert_class="danger")

    return app
