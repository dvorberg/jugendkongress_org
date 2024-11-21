import re, dataclasses, pathlib, mimetypes, copy
import xml.etree.ElementTree as etree

import flask

from . import html
from ..utils import PathSet

@dataclasses.dataclass
class MacroContext:
    markdown_file_path: pathlib.Path
    pathset: PathSet

class Macro(object):
    def __init__(self, context:MacroContext):
        self.context = context

    def register_dependent_files(self, *paths):
        """
        Add a filepath to be checked for modifications.
        """
        for path in paths:
            if type(path) == str:
                path = pathlib.Path(
                    self.context.markdown_file_path.parent, path)

            self.context.pathset.register(path)

    def get_meta(self, name):
        return self.result.get_meta(name)

    def __call__(self):
        raise NotImplemented()

ablauf_line_re = re.compile('''\
(?P<day>Freitag|Samstag|Sonntag)|
(?:
   (?:
      (?P<anschl>anschl\.?)|
      (?P<hour>\d{1,2})[:\.](?P<minute>\d{1,2})
   )
   \s+
   (?P<item>.*)
)
''', re.VERBOSE)

@dataclasses.dataclass
class AblaufItem:
    anschl: bool
    hour: int|None
    minute: int|None
    title: str

    def __init__(self, groups):
        def myint(i):
            if i is None:
                return None
            else:
                return int(i)

        self.anschl = groups["anschl"] is not None
        self.hour = myint(groups["hour"])
        self.minute = myint(groups["minute"])
        self.title = groups["item"]

    @property
    def time(self):
        if self.anschl:
            return "anschl."
        else:
            return "%02i.%02i" % ( self.hour, self.minute, )

    @property
    def timetpl(self):
        return ( self.hour, self.minute, )

    @property
    def dom(self):
        return html.div(html.time(self.time),
                        html.div(self.title, class_="title"),
                        class_="item")


@dataclasses.dataclass
class AblaufDay:
    day: str
    items: list

    def create_dom(self, times):
        div = etree.Element("div")
        div.set("class", "day col-lg")

        h = etree.Element("h4")
        h.text = self.day
        div.append(h)

        time_index = 0
        for item in self.items:
            # if not item.anschl:
            #     while time_index < len(times) and \
            #           item.timetpl != times[time_index]:
            #         blank = etree.Element("div")
            #         blank.set("class", "item blank")
            #         blank.text = " "
            #         div.append(blank)

            #         time_index += 1
            #     time_index += 1

            div.append(item.dom)

        return div

class AblaufSyntaxError(Exception): pass
class AblaufParseError(Exception): pass

class ablauf_einsetzen(Macro):
    def __call__(self, filename):
        # Find our input file and register it with the caching mechanism in
        # view_func.
        abspath = pathlib.Path(self.context.markdown_file_path.parent,
                               filename)
        self.register_dependent_files(abspath)

        current_day = None
        items_by_day = {}
        for lineno, line in enumerate(abspath.open().readlines()):
            line = line.split("#")[0]
            line = line.strip()

            if line:
                match = ablauf_line_re.match(line)
                if match is None:
                    msg = "Can’t parse %s:%i %s" % (
                        abspath.name,
                        lineno+1,
                        repr(line))
                    raise AblaufSyntaxError(msg)

                groups = match.groupdict()

                if groups["day"]:
                    current_day = groups["day"]
                else:
                    if current_day is None:
                        raise AblaufParseError("Kein Tag definiert %s:%i" % (
                            abspath.name, lineno+1))
                    if current_day not in items_by_day:
                        items_by_day[current_day] = AblaufDay(current_day, [])
                    items = items_by_day[current_day]
                    items.items.append(AblaufItem(groups))

        div = etree.Element("div")
        div.set("class", "ablauf row")

        # Which times do we need?
        times = set()
        for day in items_by_day.values():
            for item in day.items:
                if not item.anschl:
                    times.add(item.timetpl)
        times = list(times)
        times.sort()

        for day in items_by_day.values():
            div.append(day.create_dom(times))
        return div

class titelbild_einsetzen(Macro):
    def __call__(self, fn, fn_mobil):
        get_meta = self.context.result.get_meta

        self.register_dependent_files(fn, fn_mobil)

        ret = etree.Element("div")
        ret.set("class", "titelbild")

        h1 = etree.Element("h1")
        h1.text = get_meta("titel")

        st = etree.Element("small")
        st.set("class", "text-muted")
        st.text = get_meta("untertitel")
        h1.append(st)

        ret.append(h1)

        picture = etree.Element("picture")

        def add_source(src, media):
            source = etree.Element("source")
            mtype, encoding = mimetypes.guess_type(fn)

            source.set("srcset", flask.g.congress.href + src)
            source.set("type", mtype)
            source.set("media", media)
            source.text = ""

            picture.append(source)

        add_source(fn, "(min-width: 992px)")
        add_source(fn_mobil, "(max-width: 992px)")

        img = etree.Element("img")
        img.set("src", flask.g.congress.href + fn)
        picture.append(img)

        ret.append(picture)

        datum = etree.Element("div")
        datum.set("class", "datum text-muted")
        datum.text = get_meta("datum") + " • Jugendburg Ludwigstein"

        no = etree.Element("small")
        no.set("class", "text-muted")
        no.text = get_meta("nummer") + ". Lutherischer Jugendkongress"
        datum.append(no)

        ret.append(datum)

        return ret

class workshops_einsetzen(Macro):
    def __call__(self):
        congress = flask.g.congress

        ret = html.div(class_="workshops row")

        for no, workshop in enumerate(congress.workshops):
            referenten = html.div(class_="col-md-4 referenten")

            for referent, info in workshop.referenten_info:
                div = html.div()

                for picture in workshop.pictures:
                    if picture.stem.lower() == referent.lower():
                        div.append(html.img(src=picture.href,
                                            class_="img-fluid"))
                        break

                p = html.p(referent)
                if info:
                    p.append(html.br(),
                             html.small(info, class_="text-muted"))
                div.append(p)

                referenten.append(div)


            colname = f"text{no}"

            if workshop.untertitel:
                untertitel = html.small(workshop.untertitel,
                                        class_="text-muted")
            else:
                untertitel = None

            main_text = html.div(html.h5(workshop.titel,
                                         html.br(),
                                         untertitel,
                                         class_="card-title"),
                                 workshop.root_element,
                                 class_="collapse" ,
                                 id=colname)

            more_button = html.button("Mehr …",
                                      class_="btn btn-link ps-0",
                                      type="button",
                                      data_bs_toggle="collapse",
                                      data_bs_target="#" + colname)

            texts = html.div(html.div(html.div(main_text,
                                               more_button,
                                               class_="card-text"),
                                      class_="card-body"),
                             class_="col-md-8")

            card = html.div(html.h5("Workshop",
                                    class_="card-header"),
                            html.div(texts, referenten,
                                     class_="row g-0"),
                            class_="workshop card mb-4")

            ret.append(html.div(card, class_="col-md-6"))

        return ret
