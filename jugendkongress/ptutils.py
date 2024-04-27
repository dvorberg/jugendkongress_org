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

import sys, types, re, decimal
from html import escape

from flask import request

from ll.xist.ns import html
from ll.xist import xsc

from t4.web import add_url_param, set_url_param, js_string_literal
from t4.typography import (pretty_duration, pretty_bytes, pretty_german_date,
                           add_web_paragraphs)

pretty_date = pretty_german_date

from .utils import *

def checked(b):
    if b: return "checked"

def selected(b):
    if b: return "selected"

def active(b):
    if b: return "active"

def disabled(b):
    if b: return "disabled"

extension_from_url_re = re.compile(r".*\.([^\.]+)$")
def extension_from_url(url):
    match = extension_from_url_re(url)
    if match is None:
        return None
    else:
        extension, = match.groups()
        return extension

def test(condition, a, b=None):
    if condition:
        return a
    else:
        return b

def exclass(class_, *other_classes):
    names = [ class_, ] + list(other_classes)
    names = filter(lambda s: bool(s), names)
    names = [ s.strip() for s in names ]
    return " ".join(names)

def html_with_paras(s):
    s = s.replace("\r\n", "\n")
    paras = s.split("\n\n")
    paras = [ '<p>'+escape(p.strip()).replace("\n", "<br/>")+'</p>'
              for p in paras ]
    return "\n".join(paras)

def delete_onclick(title):
    eintrag = "„%s“" % title
    tmpl = ('return confirm("Möchten Sie den Eintrag " + '
            '%s + " wirklich löschen?")')
    return tmpl % ( js_string_literal(eintrag), )

__all__ = [ "js_string_literal", "pagination", "set_url_param", "checked",
            "selected", "active", "disabled", "extension_from_url", "test",
            "exclass", "html_with_paras", "selected_elkg", "delete_onclick",
            "quote_plus", "pretty_duration", "pretty_bytes",
            "pretty_german_date", "add_web_paragraphs", ]
