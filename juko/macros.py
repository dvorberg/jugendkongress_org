import re, dataclasses, pathlib
import xml.etree.ElementTree as etree

@dataclasses.dataclass
class MacroContext:
    markdown_file_path: pathlib.Path
    dependent_files: dict

class Macro(object):
    def __init__(self, context):
        self.context = context

    def register_dependent_file(self, path):
        """
        Add a filepath to be checked for modifications.
        """
        assert path.is_absolute, ValueError
        self.context.dependent_files.add(path)

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
        div = etree.Element("div")
        div.set("class", "item")

        time = etree.Element("time")
        time.text = self.time
        div.append(time)

        item = etree.Element("div")
        item.set("class", "title")
        item.text = self.title
        div.append(item)

        return div


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
        abspath = abspath.absolute()

        self.register_dependent_file(abspath)

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
