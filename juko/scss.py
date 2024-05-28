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

from flask import g, current_app as app, Response
import shutil, subprocess

scss_cache = {}

# @app.route("/scss/<path:template_path>")
def compile_scss(template_path):
    if template_path in scss_cache:
        result = scss_cache[template_path]
    else:
        rp = g.skin.resource_path(template_path)

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

    response = Response(result)
    response.headers["Content-Type"] = "text/css; charset=UTF-8"

    if app.debug:
        response.headers["Pragma"] = "no-cache"
    else:
        response.headers["Cache-Control"] = "max-age=6048000" # 10 weeks

    return response
