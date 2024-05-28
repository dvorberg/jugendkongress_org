##  Copyright 2024 by Diedrich Vorberg <diedrich@tux4web.de>
##
##  All Rights Reserved
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

import os, os.path as op, runpy

import icecream
icecream.install()

config_file = os.getenv("YOURAPPLICATION_SETTINGS",
                        os.getenv("APPLICATION_SETTINGS", None))
if config_file is None:
    raise IOError("YOURAPPLICATION_SETTINGS not set.")
elif not op.exists(config_file):
    raise IOError("Can’t read config from " + config_file)

config = runpy.run_path(config_file)

debug = bool(os.getenv("FLASK_ENV", None) == "development")
debug_sql = (os.getenv("DEBUG_SQL", None) is not None)

if not debug:
    icecream.diable()
