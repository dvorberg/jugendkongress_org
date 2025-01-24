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

import sys, os, os.path as op, time, datetime, pathlib
import chameleon, chameleon.tales

from flask import g, current_app, session, request

from . import debug
from .utils import get_site_url, rget

startup_time = time.time()

class TemplateWithCustomRenderMethod:
    auto_reload = debug

    def render(self, **kw):
        from . import authentication

        extras = {"session": session,
                  "request": request,
                  "rget": rget,
                  "user": authentication.get_user() }

        if hasattr(self, "filename") and self.filename != "<string>":
            extras["template_mtime"] = datetime.datetime.fromtimestamp(
                op.getmtime(self.filename))

        for key, value in extras.items():
            if key not in kw:
                kw[key] = value

        return super().render(**kw)

class FormatExpression(chameleon.tales.PythonExpr):
    def translate(self, expression, target):
        expression = expression.replace('"', r'\"')
        return chameleon.tales.PythonExpr.translate(
            self, 'f"' + expression + '"', target)

class CustomPageTemplateFile(TemplateWithCustomRenderMethod,
                             chameleon.PageTemplateFile):
    expression_types = {**chameleon.PageTemplateFile.expression_types,
                        **{"f": FormatExpression}}

class CustomPageTemplate(TemplateWithCustomRenderMethod,
                         chameleon.PageTemplate):
    expression_types = {**chameleon.PageTemplate.expression_types,
                        **{"f": FormatExpression}}

class CustomPageTemplateLoader(chameleon.PageTemplateLoader):
    formats = { "xml": CustomPageTemplateFile,
                "text": chameleon.PageTextTemplateFile, }

class MacrosPageTemplateWrapper(CustomPageTemplate):
    def __init__(self, macros_template, macro_name):
        self.macros_template = macros_template

        tmpl = '<metal:block metal:use-macro="macros_template[\'%s\']" />'
        super().__init__(tmpl % macro_name)

    def _builtins(self):
        builtins = chameleon.PageTemplate._builtins(self)
        builtins["macros_template"] = self.macros_template
        return builtins

class MacrosFrom:
    """
    This is a wrapper arround a Page Template containing only macro
    definitions. These are available as methods of this object.

    Macro example:

    ...
    <metal:block metal:define-macro="user-list">
       <div tal:repeat="user users">
         ... “my smart html” ...
       </div>
    </metal:block>

    mf = MacrosFrom(<page template>)
    mf.user_list(users) → “my smart html” with the users filled in

    """
    def __init__(self, template):
        self.template = template
        self._template_wrappers = {}

    def __getattr__(self, name):
        if debug:
            self._template_wrappers = {}
            self.template.cook_check()

        if not name in self._template_wrappers:
            macro = None
            for n in ( name.replace("_", "-"),
                       name, ):
                try:
                    macro = self.template.macros[n]
                except KeyError:
                    pass
                else:
                    break
            else:
                raise NameError("No macro named %s." % name)

            self._template_wrappers[name] = MacrosPageTemplateWrapper(
                self.template, n)

        return self._template_wrappers[name]

class Skin(object):
    def __init__(self, www_path):
        from . import ptutils
        from . import utils

        extra_builtins = { "skin": self,
                           "test": ptutils.test,
                           "glyphicon": self.glyphicon,
                           "ptutils": ptutils,
                           "utils": utils,
                           "g": g,
                           "sref": self.href}

        self.www_path = www_path
        self._pt_loader = CustomPageTemplateLoader(
            www_path,
            default_extension=".html",
            debug=debug,
            extra_builtins = extra_builtins)

        self.glyphicons = {}

    def resource_exists(self, path):
        return op.exists(self.resource_path(path))

    def resource_path(self, path):
        return op.join(self.www_path, path)

    def href(self, path):
        fp = pathlib.Path(self.www_path, "skin", path)
        if fp.exists:
            t = "?t=%f" % fp.stat().st_mtime
        else:
            t = "?t=%f" % startup_time

        return get_site_url() + "/skin/" + path + t

    def read(self, path):
        abspath = op.join(self.www_path, "skin", path)
        with open(abspath) as fp:
            return fp.read()

    def script_tag(self, path):
        js = self.read(path)
        return "<script><!--\n%s\n// -->\n</script>" % js

    @property
    def site_url(self):
        return get_site_url()

    def load_template(self, path):
        template = self._pt_loader.load(path)
        if debug:
            template.cook_check()
        return template

    @property
    def main_template(self):
        return self.load_template("skin/jugendkongress/main_template.pt")

    def macros_from(self, template_path):
        return MacrosFrom(self.load_template(template_path))

    def glyphicon(self, name):
        if name not in self.glyphicons:
            glyphicon_path = op.join(self.www_path, "skin", "glyphicons")
            for fn in os.listdir(glyphicon_path):
                if fn.endswith(name):
                    path = op.join(glyphicon_path, fn)
                    svg = open(path).read()
                    #svg = svg.replace('id="glyphicons-basic"', "")

                    # Remove first line and last line.
                    first, rest = svg.split("\n", 1)
                    rest, last = svg.rsplit("\n", 1)

                    self.glyphicons[name] = rest
                    break
            else:
                raise IOError(name)

        return self.glyphicons[name]
