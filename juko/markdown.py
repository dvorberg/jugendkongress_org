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
import dataclasses
from pathlib import Path

from flask import g

import markdown

from . import config

@dataclasses.dataclass
class CacheEntry:
    mtime: float
    html: str

markdown_cache = {}

def view_func(infile_path:str):
    infile_path = Path(infile_path)
    www_root = Path(config["WWW_PATH"])

    abspath = Path(www_root, infile_path)

    entry = markdown_cache.get(abspath, None)
    mtime = abspath.stat().st_mtime
    if entry is not None and entry.mtime == mtime:
        html = entry.html
    else:
        html = markdown.markdown(abspath.read_text(),
                                 extensions=["extra", "meta", "nl2br"])
        html = '<div class="markdown">' + html + '</div>'
        markdown_cache[abspath] = CacheEntry(mtime, html)

    template = g.skin.load_template("skin/jugendkongress/congress_view.pt")
    return template(html=html)
