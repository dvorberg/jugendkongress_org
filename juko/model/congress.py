import pathlib, dataclasses, re, datetime, json
from functools import cached_property

from .. import config
from ..db import dbobject, execute
from ..markdown import MarkdownResult
from ..markdown.macros import MacroContext
from ..utils import PathSet

from sqlclasses import sql

import flask


class DocumentFolder(object):
    def __init__(self, path, pathset:PathSet=PathSet()):
        self.abspath = path.absolute()
        self.relpath = path.relative_to(config["WWW_PATH"])

        self.pathset = pathset
        self.pathset.register(self.abspath)

        self._md = None
        self._rtime = None

    @property
    def href(self):
        return config["SITE_URL"] + "/" + str(self.relpath) + "/"

    @property
    def valid(self):
        return (self._rtime == self.pathset.mtime)

    @property
    def md(self):
        if self._md is None:
            result = self.abspath.glob("*.md")
            try:
                infilepath = next(result)
            except StopIteration:
                return None

            self.pathset.register(infilepath)

            self._md = MarkdownResult( infilepath.open().read(),
                                       MacroContext(
                                           markdown_file_path=infilepath,
                                           pathset=self.pathset) )
            self._rtime = self.pathset.mtime
        return self._md

    @property
    def html(self):
        return self.md.html

    @property
    def root_element(self):
        return self.md.root_element

class Picture(object):
    def __init__(self, workshop, path):
        self.workshop = workshop
        self.abspath = path

        self._href = self.workshop.href + "/" + self.abspath.name

    @property
    def href(self):
        return self._href

    @property
    def stem(self):
        return self.abspath.stem


class Workshop(DocumentFolder):
    def __init__(self, path, congress):
        super().__init__(path, congress.pathset)
        self.congress = congress

        # Pictures
        paths = list()
        for ext in ("jpg", "webp", "png"):
            paths += list(self.abspath.glob("*." + ext))
        paths.sort(key=lambda p: p.name )

        self.pathset.register(*paths)
        self._pictures = [ Picture(self, path) for path in paths ]

    @property
    def pictures(self):
        """
        A list of Picture objects in this workshop sorted alphabetically.
        .jpg, .png and .webp files are listed.
        """
        return self._pictures

    @property
    def id(self):
        if id := self.md.get_meta("id"):
            return id
        else:
            return self.abspath.stem

    @property
    def sort_key(self):
        return self.md.get_meta("signatur", self.id)

    @property
    def titel(self):
        return self.md.get_meta("titel") or self.id

    @property
    def untertitel(self):
        return self.md.get_meta("untertitel") or None

    @property
    def referenten(self):
        return self.md.get_meta("referent", as_list=True)

    @property
    def referenten_info(self):
        referenten = self.referenten
        info = self.md.get_meta("referent-info", as_list=True)
        while len(info) < len(referenten):
            info.append("")

        return zip(referenten, info)


class Congress(DocumentFolder):
    def __init__(self, congresses, path):
        super().__init__(path)
        self.congresses = congresses
        self.reset()

    def reset(self):
        self.pathset = PathSet()
        self.pathset.register(self.abspath)

        self._md = None
        self._rtime = None

        self._workshops = [ Workshop(path, self)
                            for path in self.abspath.glob("*.workshop") ]
        self._workshops.sort(key=lambda w: w.sort_key)

    @property
    def workshops(self):
        return self._workshops

    @cached_property
    def anmeldeschluss(self):
        v = self.md.get_meta("anmeldeschluss")
        try:
            return datetime.date(*[int(a) for a in v.split("-")])
        except (ValueError, TypeError):
            return None

    @property
    def titel(self):
        return self.md.get_meta("titel") or self.id

    @property
    def untertitel(self):
        return self.md.get_meta("untertitel") or None

    @property
    def nummer(self):
        return self.md.get_meta("nummer")

    year_re = re.compile(r"(\d{4}).*")
    @cached_property
    def year(self):
        match = self.year_re.match(self.abspath.name)
        return int(match.group(1))

    @property
    def registration_is_open(self):
        return ( self.congresses.latest_year == self.year
                 and self.anmeldeschluss is not None
                 and self.anmeldeschluss >= datetime.date.today())

    @property
    def controller_url(self):
        return config["SITE_URL"] + "/" + str(self.year)

    def where(self, *args):
        return sql.where("year = %i" % self.year).and_(
            sql.where(*args))

    def booking_href(self, key):
        return "%s/%i?key=%s" % ( config["SITE_URL"], self.year, key)

congress_directory_re = re.compile(r"(\d{4}).*")
class Congresses(object):
    def __init__(self):
        self._readdir()

    def _readdir(self):
        self.www_root = pathlib.Path(config["WWW_PATH"])
        def congresses():
            for p in self.www_root.iterdir():
                if p.is_dir():
                    match = congress_directory_re.match(p.name)
                    if match is not None:
                        yield int(match.group(1)), Congress(self, p),

        self._congresses = dict(sorted(list(congresses()),
                                       key=lambda tpl: tpl[0]))
        self._latest_year = max(self._congresses.keys())
        self._last_change = self.www_root.stat().st_mtime

    @staticmethod
    def readdir_maybe(method):
        def wrapper(self, *args, **kw):
            if self._last_change != self.www_root.stat().st_mtime:
                self._readdir()
            return method(self, *args, **kw)
        return wrapper

    @staticmethod
    def validate_congress(method):
        def wrapper(self, *args, **kw):
            congress = method(self, *args, **kw)
            if not congress.valid:
                congress.reset()
            return congress
        return wrapper

    @property
    @readdir_maybe
    def congresses(self):
        return self._congresses

    @property
    @readdir_maybe
    def latest_year(self):
        return self._latest_year

    @property
    @validate_congress
    def current(self):
        return self.congresses[self._latest_year]

    @validate_congress
    def by_path(self, path):
        if isinstance(path, pathlib.Path):
            path = path.name

        match = congress_directory_re.match(path)
        if match is None:
            return None
        else:
            year = int(match.group(1))
            return self.congresses.get(year, None)

    @validate_congress
    def by_year(self, year:int):
        return self.congresses.get(year, None)

class Change(object):
    def __init__(self, change:dict):
        self._errors = {}
        self._fields = set()
        self._validated = set()

        for name, value in change.items():
            name = self.normalize(name)
            self._fields.add(name)
            setattr(self, name, value)

    def normalize(self, name):
        return name.replace("-", "_")

    def __getitem__(self, name):
        return getattr(self, self.normalize(name))

    @property
    def name(self):
        return self.firstname + " " + self.lastname

    def __contains__(self, name):
        return hasattr(self, name)

    def confirm(self, field):
        self._validated.add(field)
        self._errors[field] = None

    def report(self, field, error):
        assert field in self._fields, NameError
        self._errors[field] = error

    @property
    def errors(self):
        ret = {}
        for field, error in self._errors.items():
            ret[field.replace("_", "-")] = error
        return ret

    def errors_as_json(self):
        return json.dumps(self.errors)

    @property
    def validated(self):
        return dict([ (field, getattr(self, field))
                      for field in self._validated ])

class Booking(dbobject):
    __relation__ = "booking"
    __view__ = "booking_info"

    @property
    def workshop_choices(self):
        return self._workshop_choices

    @workshop_choices.setter
    def workshop_choices(self, choices):
        if choices is None:
            self._workshop_choices = set()
        else:
            self._workshop_choices = set(choices.split(","))

    def as_dict(self):
        ret = super().as_dict()
        ret["workshop_choices"] = self.workshop_choices
        return ret

    @classmethod
    def update_by_slug(cls, year, slug, **data):
        if "lactose_intolerant" in data:
            data["lactose_intolerant"] = (data["lactose_intolerant"] == "true")

        command = sql.update(
            cls.__relation__,
            sql.where("year = %i" % year,
                      " AND slug = ", sql.string_literal(slug)), data)
        execute(command)

    @property
    def name(self):
        return self.firstname + " " + self.lastname

    def validate_me(self):
        return self.validate(Change(self.as_dict()))

    @staticmethod
    def validate(change:Change):
        errors = {}
        for name in ("address", "zip", "city", "dob"):
            if name in change:
                if not change[name]:
                    change.report(name, "Dises Feld darf nicht leer sein.")
                else:
                    change.confirm(name)

        for name in ("gender", "food_preference", "room_preference",
                     "ride_sharing_option"):
            if name in change:
                if not change[name]:
                    change.report(name, "Bitte triff eine Auswahl.")
                else:
                    change.confirm(name)

        for name in ("phone", "lactose_intolerant", "food_remarks",
                     "room_mates", "ride_sharing_start", "musical_instrument"):
            if name in change:
                change.confirm(name)

        return change

    @property
    def delete_href(self):
        return "%s/%i/deletebooking?key=%s" % ( config["SITE_URL"],
                                         self.year, self.slug)

if __name__ == "__main__":
    # Test this.
    import sys
    from juko import config

    congresses = Congresses()
