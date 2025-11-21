from xml.etree.ElementTree import Element

class _html(Element):
    def __init__(self, *children, **attrs):
        super().__init__(self.__class__.__name__)

        for name, value in attrs.items():
            if name.endswith("_"):
                name = name[:-1]
            name = name.replace("_", "-")
            self.set(name, value)

        for child in children:
            if child is None:
                pass
            elif type(child) == str:
                if self.text is None:
                    self.text = child
                else:
                    self.text += child
            else:
                self.append(child)

    def append(self, *args):
        for a in args:
            super().append(a)

class div(_html): pass
class p(_html): pass
class h1(_html): pass
class h2(_html): pass
class h3(_html): pass
class h4(_html): pass
class h5(_html): pass

class picture(_html): pass
class source(_html): pass
class figure(_html): pass
class figcaption(_html): pass

class span(_html): pass
class strong(_html): pass
class small(_html): pass
class a(_html): pass
class img(_html): pass
class time(_html): pass
class button(_html): pass

class br(_html): pass
