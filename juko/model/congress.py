import pathlib, dataclasses, re, datetime, json, tomllib, itertools
from functools import cached_property

from .. import config
from ..db import dbobject, execute, Result, with_
from ..markdown import MarkdownResult
from ..markdown.macros import MacroContext
from ..utils import PathSet

from sqlclasses import sql
from PIL import Image

from ll.xist import xsc
from ll.xist.ns import html

import flask

class DocumentFolder(object):
    def __init__(self, path, pathset:PathSet=PathSet()):
        self.abspath = path.absolute()
        self.relpath = path.relative_to(config["WWW_PATH"])

        self.pathset = pathset
        self.pathset.register(self.abspath)

        self._md = None
        self._meta = None
        self._rtime = None
        self._rendering_md = False

    titel_h1_re = re.compile(r"<title>\s*(?:\d+\s*[-–]\s*)?([^<]*)</title>")
    untertitel_h2_re = re.compile(r"<h2[^>]*>\s*([^<]+)\s*</h2>")
    @cached_property
    def meta(self):
        if self._meta is None:
            meta_file = pathlib.Path(self.abspath, "meta.toml")
            if meta_file.exists():
                self.pathset.register(meta_file_path)
                self._meta = tomllib.load(meta_file.open("rb"))

            html_file = pathlib.Path(self.abspath, "index.html")
            if html_file.exists():
                html = html_file.open().read()

                if self._meta is None:
                    self._meta = {}

                result = self.titel_h1_re.search(html)
                if result is not None and not "titel" in self._meta:
                    self._meta["titel"] = result.group(1)

                result = self.untertitel_h2_re.search(html)
                if result is not None and not "untertitel" in self._meta:
                    self._meta["untertitel"] = result.group(1)

        return self._meta

    def get_meta(self, name, default="", as_list=False):
        if self.meta:
            r = self.meta.get(name, default)
            if as_list and type(r) != list:
                return [ r, ]
            else:
                return r
        return self.md.get_meta(name, default, as_list)

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

            if self._rendering_md:
                raise Exception("Recursive rendering of " + str(infilepath))
            self._rendering_md = True
            self._md = MarkdownResult( infilepath.open().read(),
                                       MacroContext(
                                           markdown_file_path=infilepath,
                                           pathset=self.pathset,
                                           congress=self.congress) )
            self._md.convert()
            self._rendering_md = False
            self._rtime = self.pathset.mtime
        return self._md

    @property
    def congress(self):
        raise NotImplementedError()

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
        self._congress = congress

        # Pictures
        paths = list()
        for ext in ("webp", "jpg", "jpeg", "png"):
            paths += list(self.abspath.glob("*." + ext))
        paths.sort(key=lambda p: p.name )

        self.pathset.register(*paths)
        self._pictures = [ Picture(self, path) for path in paths ]

    @property
    def congress(self):
        return self._congress

    @property
    def pictures(self):
        """
        A list of Picture objects in this workshop sorted alphabetically.
        .jpg, .png and .webp files are listed.
        """
        return self._pictures

    @property
    def id(self):
        if id := self.get_meta("id"):
            return id
        else:
            return self.abspath.stem

    @property
    def sort_key(self):
        return self.get_meta("signatur", self.id)

    @property
    def titel(self):
        return self.get_meta("titel") or self.id

    @property
    def untertitel(self):
        return self.get_meta("untertitel") or None

    @property
    def referenten(self):
        return self.get_meta("referent", as_list=True)

    @property
    def referenten_info(self):
        referenten = self.referenten
        info = self.get_meta("referent-info", as_list=True)
        while len(info) < len(referenten):
            info.append("")

        return zip(referenten, info)

    @property
    def phasen(self):
        w = self.get_meta("workshopphasen", "")
        try:
            return [ int(a) for a in w.split(",") if a ]
        except ValueError:
            raise ValueError("Ungültige Workshoppphase in %s: %s" % (
                self.id, repr(w)))

    @property
    def teilnehmer_max(self):
        return int(self.get_meta("teilnehmer-max", 15))

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and other.id == self.id)

    def __repr__(self):
        return f"<WS:{self.id}>"

@dataclasses.dataclass
class Workshopphase:
    number: int
    description: str

class Congress(DocumentFolder):
    def __init__(self, congresses, path):
        super().__init__(path)
        self.congresses = congresses
        self.reset()

    @property
    def anmeldung_from_name(self):
        return self.get_meta("anmeldungs-from-name")

    @property
    def congress(self):
        return self

    def reset(self):
        self.pathset = PathSet()
        self.pathset.register(self.abspath)

        self._md = None
        self._rtime = None

        workshops = [ Workshop(path, self)
                            for path in self.abspath.glob("*.workshop") ]
        workshops.sort(key=lambda w: w.sort_key)

        self._workshops = dict( [(workshop.id, workshop,)
                                 for workshop in workshops] )

    @property
    def workshops(self):
        return self._workshops.values()

    def workshop_by_id(self, workshop_id):
        return self._workshops[workshop_id]

    @cached_property
    def anmeldeschluss(self):
        v = self.get_meta("anmeldeschluss")
        try:
            return datetime.date(*[int(a) for a in v.split("-")])
        except (ValueError, TypeError):
            return None

    @cached_property
    def startdatum(self):
        v = self.get_meta("startdatum")
        try:
            return datetime.date(*[int(a) for a in v.split("-")])
        except (ValueError, TypeError):
            return None

    @property
    def titel(self):
        return self.get_meta("titel")

    @property
    def untertitel(self):
        return self.get_meta("untertitel") or None

    @property
    def nummer(self):
        return self.get_meta("nummer")

    year_re = re.compile(r"(\d{4}).*")
    @cached_property
    def year(self):
        match = self.year_re.match(self.abspath.name)
        return int(match.group(1))

    @property
    def registration_is_open(self):
        return ( self.congresses.latest_year >= self.year
                 and self.anmeldeschluss is not None
                 and self.anmeldeschluss >= datetime.date.today() )

    @property
    def controller_url(self):
        return config["SITE_URL"] + "/" + str(self.year)

    def where(self, *args):
        return sql.where("year = %i" % self.year).and_(
            sql.where(*args))

    def booking_href(self, key):
        return "%s/%i?key=%s" % ( config["SITE_URL"], self.year, key)

    def find_og_image(self):
        names = []
        for name in ("titelbild", "title"):
            for ext in ( "webp", "jpg", "png"):
                names.append(name + "." + ext)

        found = False
        for name in names:
            og_image_path = pathlib.Path(self.abspath, name)
            if og_image_path.exists():
                found = True
                break

        if not found:
            return None
        else:
            return og_image_path

    @property
    def og_image_url(self):
        if image_path := self.find_og_image():
            return self.href + image_path.name
        else:
            return None

    @property
    def og_image_size(self):
        if image_path := self.find_og_image():
            img = Image.open(str(image_path))
            return img.size
        else:
            return None

    @property
    def workshopphasen(self):
        ret = getattr(flask.g, "congress_workshopphasen", None)

        if ret is None:
            phasen = set()
            for workshop in self.workshops:
                for phase in workshop.phasen:
                    phasen.add(phase)

            numbers = list(phasen)
            numbers.sort()

            cursor = execute("SELECT number, description FROM workshop_phases "
                             "WHERE year = %i" % self.year)
            info = dict(cursor.fetchall())

            ret = [ Workshopphase(number, info.get(number, ""))
                    for number in numbers ]
            flask.g.congress_workshopphasen = ret

        return ret

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

    def __iter__(self):
        return iter(self._congresses.values())

    @property
    def archive(self):
        ret = list(self._congresses.values())
        if ret:
            del ret[-1]
            ret.reverse()
        return ret

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

def food_preference_html(food_preference):
    return { None: html.strong("∅", class_="text-danger"),
             "meat": "Fleisch",
             "vegetarian": "vegitarisch",
             "vegan": "vegan"
            }[food_preference]

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

    @property
    def age_then(self):
        if self.congress.startdatum and self.dob:
            delta = self.congress.startdatum - self.dob
            return int(delta.days / 365.25)
        else:
            return None

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
                     "mode_of_travel"):
            if name in change:
                if not change[name]:
                    change.report(name, "Bitte triff eine Auswahl.")
                else:
                    change.confirm(name)

        for name in ("phone", "lactose_intolerant", "remarks",
                     "room_mates", "ride_sharing_start",
                     "musical_instrument",
                     "rail_arrival_time", "rail_departure_time",):
            if name in change:
                change.confirm(name)

        for name in ("rail_arrival_time", "rail_departure_time",
                     "ride_sharing_start"):
            if name in change:
                v = getattr(change, name)
                if v is not None and hasattr(v, "strip"):
                    v = v.strip()
                if not v:
                    setattr(change, name, None)

        return change

    @property
    def gender_symbol(self):
        if self.gender == "male":
            return "♂"
        elif self.gender == "female":
            return "♀"
        elif self.gender == "nn":
            return "◦"
        else:
            return "∅"

    @property
    def room_preference_html(self):
        if self.room_preference is None:
            return '<strong class="text-danger">∅</strong>'
        else:
            return self.room_preference.split(" ")[0]

    @property
    def congress(self):
        return flask.g.congresses.by_year(self.year)

    @property
    def href(self):
        return self.congress.booking_href(self.slug)

    @property
    def delete_href(self):
        return "%s/%i/deletebooking?key=%s" % ( config["SITE_URL"],
                                         self.year, self.slug)

    @property
    def resolved_room_mates(self):
        # This returns a list pairs matching a found name or email address
        # to a Booking object.
        if not hasattr(self, "_resolved_room_mates"):
            raise ValueError("Room mates not resolved, yet.")
        else:
            return self._resolved_room_mates

    @property
    def found_room_mates(self):
        # This returns a list of resolved bookings that have been found.
        return [ booking
                 for (name, booking) in self.resolved_room_mates
                 if booking is not None ]


    def resolve_room_mates(self, keys_to_bookings):
        room_mates = self.room_mates.replace(
            ",", "\n").replace("/", "\n").split("\n")
        ret = []
        for line in room_mates:
            key = sql.normalize_whitespace(line).lower()
            ret.append( (line, keys_to_bookings.get(key, None),) )
        self._resolved_room_mates = ret
        return ret

    def make_room_mates_html(self, room=None):
        ret = xsc.Frag()
        for line, booking in self.resolved_room_mates:
            if booking is None:
                ret.append(html.div(line, class_="text-danger"))
            else:
                if room:
                    if booking in room.occupants:
                        symbol = " ✓"
                    else:
                        symbol = " ❌"
                else:
                    symbol = xsc.Frag()

                ret.append(html.div(booking.name, symbol,
                                    class_="text-no-wrap text-success"))
        return ret

    @property
    def max_beds(self):
        if self.room_preference == "2-3 beds":
            return 3
        elif self.room_preference == "4-8 beds":
            return 8
        else:
            return 0

    @property
    def min_beds(self):
        if self.room_preference == "2-3 beds":
            return 2
        elif self.room_preference == "4-8 beds":
            return 4
        else:
            return 255

    @property
    def food_preference_html(self):
        return food_preference_html(self.food_preference)

    @property
    def ROOM(self):
        if self.room_overwrite:
            return self.room_overwrite.upper()
        else:
            if self.room is None:
                return "∅"
            else:
                return self.room.upper()

    @property
    def needs_payment(self):
        return self.role not in { "team", "speaker" }

    @property
    def paymentcls(self):
        if not self.needs_payment:
            return "secondary"
        else:
            if self.has_payed:
                return "success"
            else:
                return "danger"

    @staticmethod
    def format_pretty_checkin_time(checkin):
        if checkin is None:
            return ""
        else:
            return checkin.strftime("%a %H.%M")

    @property
    def pretty_checkin_time(self):
        return self.format_pretty_checkin_time(self.checkin)

    @property
    def pretty_rail_arrival_time(self):
        return self.rail_arrival_time.strftime("%H.%M") + " Uhr"

    @property
    def pretty_rail_departure_time(self):
        return self.rail_departure_time.strftime("%H.%M") + " Uhr"

    def __repr__(self):
        if hasattr(self, "role"):
            return f"<{self.role[:4]}:{self.name}>"
        else:
            return f"<{self.name}>"

class BookingForWorkshopAssignment(Booking):
    __view__ = "workshop_assignment_info"

def resolve_room_mates(bookings):
    # Create a dict matching (lower case) names and email-addresses
    # to bookings.
    d = {}
    for booking in bookings:
        d[booking.name.lower()] = booking
        d[booking.email] = booking

    # Now go through each of the names listed in the bookings
    # and see if we can find them.
    for booking in bookings:
        booking.resolve_room_mates(d)

class BookingForNameForm(dbobject):
    __relation__ = "booking"
    __view__ = "booking_for_name_form"

class RoomResult(Result):

    @dataclasses.dataclass
    class Section:
        title: str
        rooms: list

    @property
    def sections(self):
        sections = []
        for title, rooms in itertools.groupby(self, lambda room: room.section):
            sections.append(self.Section(title, list(rooms)))
        return sections

class Room(dbobject):
    __view__ = "room_info"
    __result_class__ = RoomResult

    @with_
    def with_year(self, year):
        return sql.with_(("room_info",
                          sql.select( ("room.*",
                                       sql.expression("(year = %i)" % year,
                                                      " AS booked"),
                                       "beds_overwrite",),
                                      ( "room", ),
                                      sql.left_join(
                                          "booked_rooms",
                                          "room_no = room.no "
                                          "AND year = %i" % year)),))

    @property
    def NO(self):
        return self.no.upper()

    @property
    def full(self):
        return (len(self.occupants) >= (self.beds_overwrite or self.beds))

    @property
    def overfull(self):
        return (len(self.occupants) > (self.beds_overwrite or self.beds))


    def __repr__(self):
        return f"<{self.__class__.__name__} {self.NO}>"



if __name__ == "__main__":
    # Test this.
    import sys
    from juko import config

    congresses = Congresses()
