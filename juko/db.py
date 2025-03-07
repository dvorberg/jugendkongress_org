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

import os.path as op, json
import psycopg2, datetime, types
from flask import g, current_app, request

from termcolor import colored
from sqlclasses import sql

from . import config, debug, debug_sql

from ll.xist import xsc
from ll.xist.ns import html

from t4.typography import pretty_german_date

from .utils import rget

class DbException(Exception): pass
class DbUsageException(Exception): pass

sql_backend = sql.Backend(psycopg2, None)
def rollup_sql(*query):
    if debug_sql:
        debsql, params, = sql.rollup(sql_backend, *query, debug=True)
    return sql.rollup(sql_backend, *query)

def get_dbconn():
    return g.dbconn

#def init_app(app):
#    app.teardown_appcontext(close_dbconn)

# def close_dbconn(e=None):
#     dbconn = g.pop("dbconn", None)
#     if dbconn is not None:
#         dbconn.rollback()
#         dbconn.close()

class CursorDebugWrapper(object):
    def __init__(self, cursor):
        self._cursor = cursor

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def execute(self, query, vars=None):
        sql = self._cursor.mogrify(query, vars)
        print(colored(sql.decode("utf-8", errors="replace"), "cyan"))
        return self._cursor.execute(sql)

    def __enter__(self):
        return CursorDebugWrapper(self._cursor.__enter__())

    def __exit__(self, type, value, traceback):
        return self._cursor.__exit__(type, value, traceback)

    def __iter__(self):
        return self._cursor.__iter__()

def cursor():
    cursor = get_dbconn().cursor()

    if debug_sql:
        return CursorDebugWrapper(cursor)
    else:
        return cursor

def commit():
    get_dbconn().commit()

def rollback():
    get_dbconn().rollback()

def insert_from_dict(relation, d, retrieve_id=True, sequence_name=None):
    if sequence_name is not None:
        retrieve_id = True

    command = sql.insert(relation, list(d.keys()), [ d, ])

    with cursor() as cc:
        command, params = rollup_sql(command)
        cc.execute(command, params)

        if not "id" in d and retrieve_id:
            if sequence_name is None:
                #if isinstance(relation, sql.relation):
                #    name = relation.name.name
                #else:
                #    name = str(relation)
                #    seqence_name = '%s_id_seq' % name
                sequence_name = "myid"

            cc.execute("SELECT CURRVAL('%s')" % sequence_name)
            id, = cc.fetchone()
            return id
        else:
            return None


class SQLRepresentation(type):
    def __new__(cls, name, bases, dct):
        ret = super().__new__(cls, name, bases, dct)

        schema = None
        if ret.__schema__ is None:
            for base in bases:
                if getattr(base, "__schema__", None) is not None:
                    schema = base.__schema__
                    break
        else:
            schema = ret.__schema__

        if bases != ( object, ):
            if ret.__relation__ is None:
                ret.__relation__ = sql.relation(name, schema)
            elif type(ret.__relation__) is str:
                ret.__relation__ = sql.relation(ret.__relation__, schema)
            else:
                if not isinstance(ret.__relation__, sql.relation):
                    raise TypeError(
                        "__relation__ must be string or sql.relation instance.")

            if ret.__view__ is None:
                ret.__view__ = ret.__relation__
            elif type(ret.__view__) is str:
                ret.__view__ = sql.relation(ret.__view__, schema)
            else:
                if not isinstance(ret.__relation__, sql.relation):
                    raise TypeError(
                        "__view__ must be string or sql.relation instance.")

        return ret

class Result(list):
    def __init__(self, cursor, dbobject_class, clauses=[]):
        self.dbobject_class = dbobject_class

        self.where = None
        self._count = None
        if clauses:
            for clause in clauses:
                if isinstance(clause, sql.where):
                    self.where = clause
                    break

        list.__init__(self, [ dbobject_class(cursor.description, tpl)
                              for tpl in cursor ])

    def __getitem__(self, key):
        if isinstance(key, slice):
            ret = self.__class__([], self.dbobject_class, [self.where])
            for a in super().__getitem__(key):
                ret.append(a)
            return ret
        else:
            return super().__getitem__(key)

    def count(self):
        """
        Issue a SELECT COUNT(*) SQL query for this dbclass and where
        clause.  Raises ValueError if not sql.where() clause was used
        when selecting this result.
        """
        if self.where:
            if self._count is None:
                self._count =  self.dbobject_class.count(self.where)

            return self._count
        else:
            raise DbUsageException(
                "No WHERE clause provided with this result.")

class PagedResultWrapper:
    def __init__(self, pagesize, page, url_for_page_f, result):
        self.pagesize = pagesize
        self.page = page
        self.url_for_page = url_for_page_f
        self.result = result

    def __getattr__(self, name):
        return getattr(self.result, name)

    @property
    def pagination(self):
        if self.count() <= self.pagesize:
            return

        def li(something, extra=None):
            if extra:
                cls = " " + extra
            else:
                cls = ""
            return html.li(something, class_="page-item " + cls)

        def a(page, text=None, **kw):
            if text is None:
                text = str(page+1)

            return html.a(text,
                          href=self.url_for_page(page),
                          class_="page-link", **kw)

        maxpage = (self.result.count() // self.pagesize)
        if self.result.count() % self.pagesize > 0:
            maxpage += 1

        if self.page == 0:
            previous = li(a(0, "«"), "disabled")
        else:
            previous = li(a(self.page - 1, "«"))

        if self.page >= maxpage-1:
            next_ = li(a(maxpage, "»"), "disabled")
        else:
            next_ = li(a(self.page + 1, "»"))

        pages = []
        for p in range(maxpage):
            if p == self.page:
                active = "active"
            else:
                active = ""

            pages.append(li(a(p), extra=active))

        return html.nav(html.ul(previous,
                                pages,
                                next_,
                                class_="pagination"))

    def __iter__(self):
        return self.result.__iter__()


class dbobject(object, metaclass=SQLRepresentation):
    __schema__ = None
    __relation__ = None
    __view__ = None
    __result_class__ = Result
    __primary_key_column__ = "id"

    def __init__(self, description, values):
        if values is None:
            raise ValueError("Can’t construct dbobject form None.")

        self._column_names = []
        for column, value in zip(description, values):
            try:
                setattr(self, column.name, value)
            except AttributeError:
                #raise AttributeError("Can’t set " + column.name)
                setattr(self, "_" + column.name, value)

            self._column_names.append(column.name)

        self.update_db = self.update_db_instance

    @classmethod
    def from_dict(cls, data):
        self = cls( (), () )
        for key, value in data.items():
            try:
                setattr(self, key, value)
            except AttributeError:
                #raise AttributeError("Can't set attribute %s to %s" % (
                #    key, repr(value)))
                setattr(self, "_" + key, value)
        return self

    def as_dict(self):
        ret = {}
        for name, value in self.__dict__.items():
            if not name.startswith("_") and \
               not type(value) is types.MethodType:
                ret[name] = value

        return ret

    def as_json(self):
        def custom_json(obj):
            if isinstance(obj, (datetime.date,
                                datetime.datetime,
                                datetime.time)):
                return { "type": obj.__class__.__name__,
                         "isoformat": obj.isoformat() }
            elif isinstance(obj, set):
                return list(obj)
            else:
                raise TypeError(f"Cannot serialize object of {type(obj)}")

        return json.dumps(self.as_dict(), default=custom_json)

    def rget(self, parameter, default=None):
        value = rget(parameter)
        if value is not None:
            return value
        else:
            if hasattr(self, "form_" + parameter):
                ret = getattr(self, "form_" + parameter)

                if callable(ret):
                    ret = ret()
            else:
                ret = getattr(self, parameter, default)

            if ret is None:
                return ""
            elif type(ret) is str:
                return ret
            elif isinstance(ret, datetime.date):
                return pretty_german_date(ret)
            elif type(ret) is int:
                return str(ret)
            else:
                raise NotImplementedError(
                    "Form-format for %s" % repr(type(ret)))

    def rint(self, parameter, default=None):
        ret = self.rget(parameter, default)
        if ret == "":
            return None
        else:
            return int(ret)

    def rchecked(self, parameter, default=None):
        if request.method == "POST":
            return (parameter in request.form)
        else:
            return getattr(self, parameter, default)

    @classmethod
    def primary_key_literal(cls, value):
        return sql.find_literal_maybe(value)

    @classmethod
    def primary_key_where(cls, value):
        # Return an sql.where() instance identifying this dbobject to the db.
        literal = cls.primary_key_literal(value)
        return sql.where(cls.__primary_key_column__, " = ", literal)

    @classmethod
    def update_db(cls, primary_key, **data):
        command = sql.update(cls.__relation__ or cls.__view__,
                             cls.primary_key_where(primary_key), data)
        execute(command)

    def update_db_instance(self, **data):
        self.__class__.update_db(getattr(self, self.__primary_key_column__),
                                         **data)

    @classmethod
    def select_query(cls, *clauses):
        return sql.select("*", [cls.__view__,], *clauses)

    @classmethod
    def delete(cls, where):
        execute(sql.delete(cls.__view__, where))

    @classmethod
    def empty(cls):
        query = cls.select_query(sql.where("false"))
        with cursor() as c:
            query, params = rollup_sql(query)
            c.execute(query, params)
            values = []
            for a in c.description:
                values.append(None)
            return cls(c.description, values)

    @classmethod
    def count(cls, *clauses):
        query = sql.select("COUNT(*)", [cls.__view__,], *clauses)
        query, params = rollup_sql(query)
        with cursor() as cc:
            cc.execute(query, params)
            count, = cc.fetchone()
        return count

    @classmethod
    def select(cls, *clauses):
        with cursor() as c:
            query = cls.select_query(*clauses)
            query, params = rollup_sql(query)
            c.execute(query, params)
            return cls.__result_class__(c, cls, clauses)

    @classmethod
    def select_paged(cls, pagesize, page, url_for_page_f, *clauses):
        clauses = list(clauses)
        clauses.append(sql.offset(page*pagesize))
        clauses.append(sql.limit(pagesize))

        return PagedResultWrapper(pagesize, page, url_for_page_f,
                                  cls.select(*clauses))

    @classmethod
    def select_by_primary_key(cls, value):
        return cls.select_one(cls.primary_key_where(value))

    @classmethod
    def select_one(cls, *clauses):
        for clause in clauses:
            if isinstance(clause, sql.limit):
                break
        else:
            clauses = list(clauses)
            clauses.append(sql.limit(1))

        result = cls.select(*clauses)
        if len(result) == 0:
            return None
        else:
            return result[0]


def execute(command, parameters=()):
    if isinstance(command, sql.Part):
        if parameters:
            raise ValueError("Can’t provide parameters with t4.sql statement.")
        command, parameters = rollup_sql(command)

    cc = cursor()
    cc.execute(command, parameters)
    return cc

def execute_with_template(template_file_name, parameters=(), **kw):
    with open(op.join(config["SQL_QUERY_PATH"], template_file_name)) as fp:
        template = fp.read()
    command = template.format(**kw)
    return execute(command, parameters)

def query(command, parameters=(), dbobject_class=dbobject):
    if isinstance(command, sql.Part):
        if parameters:
            raise ValueError("Can’t provide parameters with t4.sql statement.")
        command, parameters = rollup_sql(command)

    with cursor() as cc:
        cc.execute(command, parameters)
        return dbobject_class.__result_class__(cc, dbobject_class)

def select_one(command, parameters=(), dbobject_class=dbobject):
    if isinstance(command, sql.Part):
        if parameters:
            raise ValueError("Can’t provide parameters with t4.sql statement.")
        command, parameters = rollup_sql(command)

    with cursor() as cc:
        cc.execute(command, parameters)
        tpl = cc.fetchone()
        if tpl is None:
            return None
        else:
            return dbobject_class(cc.description, tpl)

def query_one(command, parameters=()):
    if isinstance(command, sql.Part):
        if parameters:
            raise ValueError("Can’t provide parameters with t4.sql statement.")
        command, parameters = rollup_sql(command)

    with cursor() as cc:
        cc.execute(command, parameters)
        return cc.fetchone()

class with_(classmethod):
    def __init__(self, with_f):
        self.with_f = with_f
        super().__init__(self.__call__)

    def __call__(self, dbclass, *args, **kw):
        with_f = self.with_f

        class wrapper:
            def select_query(self, *clauses):
                return sql.Query( with_f(dbclass, *args, **kw), " ",
                                  dbclass.select_query(*clauses), )

            def select(self, *clauses):
                with cursor() as c:
                    query = self.select_query(*clauses)
                    query, params = rollup_sql(query)
                    c.execute(query, params)
                    return dbclass.__result_class__(c, dbclass, clauses)

            def __getattr__(self, name):
                return getattr(dbclass, name)

        return wrapper()
