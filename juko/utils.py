import sys, functools, inspect, collections, re
from flask import current_app, request, redirect as flask_redirect
from urllib.parse import urlencode, quote_plus

from t4.title_to_id import title_to_id
from t4.web import set_url_param
from sqlclasses import sql

from ll.xist import xsc
from ll.xist.ns import html


def redirect(url, **kw):
    if kw:
        if "?" in url:
            a, b = url.split("?", 1)
            url = a
            params = "?" + b + "&" + urlencode(kw, quote_via=quote_plus)
        else:
            params = "?" + urlencode(kw, quote_via=quote_plus)
    else:
        params = ""

    if url.startswith("/"):
        url = get_site_url() + url

    return flask_redirect(url + params)

def get_www_url(path, **kw):
    if kw:
        params = "?" + urlencode(kw, quote_via=quote_plus)
    else:
        params = ""

    return current_app.config["SITE_URL"] + params

def get_site_url(**kw):
    return get_www_url("/", **kw)

def rget(key, default=None):
    if key in request.args:
        return request.args[key]
    else:
        return request.form.get(key, default)

class RCheckedDefault: pass
def rchecked(key, default=RCheckedDefault):
    """
    Also see dbobject.rchecked()
    """
    if request.method == "POST":
        return (key in request.form)
    else:
        if default is RCheckedDefault:
            return None
        else:
            return default


def call_from_request(function, *args, **kw):
    # Assemble parameters from the current request.
    signature = inspect.signature(function)

    empty = inspect.Parameter.empty
    for name, param in signature.parameters.items():
        if name in kw:
            continue

        if param.default is not empty:
            kw[name] = param.default

        if issubclass(param.annotation, list):
            value = request.form.getlist(name)
            kw[name] = value
        else:
            value = rget(name, empty)
            if value is not empty:
                value = rget(name)

                # If an annotation has been supplied,
                # cast the value.
                if param.annotation is not empty:
                    try:
                        value = param.annotation(value)
                    except ValueError as e:
                        raise ValueError("%s: %s" % ( name, str(e), ))

                kw[name] = value

    return function(*args, **kw)

def gets_parameters_from_request(func):
    @functools.wraps(func)
    def wraped_for_parameters_from_request(*args, **kw):
        return call_from_request(func, *args, **kw)
    return wraped_for_parameters_from_request


class ObjFromDict:
    def __init__(self, d):
        self.d = d

    def __getitem__(self, key):
        return self.d[key]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def get(self, key, default=sys):
        try:
            return self[key]
        except KeyError:
            if default is sys:
                raise
            else:
                return default


class FormParamOption(object):
    sql_expressoin_class = sql.where

    def __init__(self, expression, label, group=None,
                 extra_button_class=None, id=None,):
        """
        `expression` may be a string or an sql.orderby object.
        """
        if type(expression) is str:
            self.expression = self.sql_expressoin_class(expression)
        else:
            self.expression = expression

        self.label = label

        if id:
            self.id = id
        else:
            if group:
                self.id = title_to_id(f"{label} {group}")
            else:
                self.id = title_to_id(label)

        self.group = group
        self.extra_button_class = extra_button_class

    def __eq__(self, other):
        if type(other) == str:
            return (self.id == other)
        elif type(other) == type(self):
            return (self.id == other.id)
        else:
            return False

    def sql_clause(self):
        if type(self.expression) == str:
            return sql.orderby(self.expression)
        else:
            return self.expression

class FormParamHandler(object):
    option_class = FormParamOption

    def __init__(self, options, param_name, auto_submit=False):
        self.options = collections.OrderedDict()

        for o in options:
            if type(o) == tuple:
                option = self.option_class(*o)
            else:
                option = o

            if option.id in self.options:
                raise KeyError(f"Duplicate param id: {repr(option.id)}")
            self.options[option.id] = option

        self.param_name = param_name
        self.auto_submit = auto_submit

        self.default = list(self.options)[0]


    @property
    def active(self):
        ret = rget(self.param_name) or self.default

        # We need to check if the option exists, because the identifyer
        # may have been renamed, but somone might still have an old
        # cookie arround.
        if not ret in self.options:
            return self.options[self.default]
        else:
            return self.options[ret]

    def sql_clause(self):
        return self.active.sql_clause()

    def button_for(self, option, color):
        cls = [ "btn", ]
        if color:
            cls.append(color)

        if option.extra_button_class:
            cls.append(option.extra_button_class)

        return html.button( option.label, type="button",
                            class_=" ".join(cls),
                            **{"data-id": option.id} )

    def widget(self):
        cls = ["formparam-widget", f"{self.param_name}-widget"]

        if self.auto_submit:
            cls.append("auto-submit");

        ret = html.div(class_="btn-toolbar", role="toolbar")
        buttons = None
        current_group = sys

        if request.method == "POST":
            active = self.active
        else:
            active = None

        for option in self.options.values():
            if option.group != current_group:
                buttons = html.div(class_="btn-group me-2")
                ret.append(buttons)
                current_group = option.group

            if option == active:
                color = "btn-primary"
            else:
                color = "btn-secondary"

            buttons.append(self.button_for(option, color))

        if len(ret) == 1:
            ret = ret[0]

        ret["class"] += " " + " ".join(cls)
        ret["data-for"] = self.param_name
        return xsc.Frag(ret, html.input(name=self.param_name, type="text",
                                        class_="formparam-input",
                                        **{"data-for": self.param_name}))

class empty_orderby_t:
    def display_class(self, t):
        return ""

class OrderByOption(FormParamOption):
    sql_expressoin_class = sql.orderby

class OrderByHandler(FormParamHandler):
    option_class = OrderByOption

# empty_orderby = empty_orderby_t()

class PaginationHandler(FormParamHandler):
    def __init__(self, pagesize, count):
        self.options = []

        self.param_name = "page"
        self.pagesize = pagesize
        self.count = count

    @property
    def page(self):
        ret = int(rget("page", 0))
        if ret > int(self.count / self.pagesize):
            ret = 0
        return ret

    def sql_clauses(self):
        return ( sql.offset(self.page*self.pagesize),
                 sql.limit(self.pagesize), )

    def widget(self, extra_class="", **kw):
        """
        extra_class => .pagination-large, .pagination-small,
                           or .pagination-mini
        """
        if self.count is None: return xsc.Frag()
        if self.count <= self.pagesize: return xsc.Frag()

        page = int(rget("page", "0"))

        ret = html.nav()
        ul = html.ul(class_="pagination " + extra_class)
        ret.append(ul)

        pagecount = int(self.count / self.pagesize)
        if self.count % self.pagesize > 0:
            pagecount += 1

        def li(p, text=None):
            if text is None: text = str(p+1)
            if p >= 0 and p < pagecount:
                href = str(p)
                if p == page:
                    cls = "active"
                else:
                    cls = ""
            else:
                href = None
                cls = "disabled"

            ul.append(html.li(html.a(text, href=href,
                                     class_="page-link"),
                              class_="page-item " + cls))

        li(page-1, "«")
        for a in range(pagecount): li(a)
        li(page+1, "»")

        ret.append(html.input(name=self.param_name, type="text",
                              class_="formparam-input",
                              **{"data-for": self.param_name}))

        return ret

class ViewOption(FormParamOption):
    def __init__(self, label, id=None, group=None, extra_button_class=None):
        super().__init__(None, label, group, extra_button_class, id)

    def sql_clause(self):
        raise NotImplementedError()

class ViewsHandler(FormParamHandler):
    option_class = ViewOption

class NeverMatch(object):
    def __eq__(self, other):
        return False

class PathSet(set):
    def __init__(self, *paths):
        super().__init__()
        self.register(*paths)

    def register(self, *paths):
        for path in paths:
            self.add(path.absolute())

    @property
    def mtime(self):
        try:
            return max([ path.stat().st_mtime for path in self ])
        except FileNotFoundError:
            return NeverMatch()

subsitution_re = re.compile(r"\$\{([^\}]+)\}")
def process_template(template, **kw):
    def replacer(match):
        expression = match.group(1)
        return str(eval(expression, kw))

    return subsitution_re.sub(replacer, template)
