import pathlib, dataclasses, re
from .. import config

@dataclasses.dataclass
class Congress(object):
    path: pathlib.Path

    @classmethod
    def from_path(Congress, path:pathlib.Path):
        return Congress(path)

    @property
    def href(self):
        return config["SITE_URL"] + "/" + self.path.name + "/"

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
                        yield int(match.group(1)), Congress.from_path(p),

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

    @property
    @readdir_maybe
    def congresses(self):
        return self._congresses

    @property
    @readdir_maybe
    def latest_year(self):
        return self._latest_year

    @property
    @readdir_maybe
    def current(self):
        return self._congresses[self._latest_year]

if __name__ == "__main__":
    # Test this.
    import sys
    from juko import config

    congresses = Congresses()
    ic(congresses.current.href)
