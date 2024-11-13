from xml.etree.ElementTree import Element

class _html(Element):
    def __init__(self, *children, **attrs):
        super().__init__(self.__class__.__name__)
        for name, value in attrs.items():
            if name.endswith("_"):
                name = name[:-1]
            self.set(name, value)

        for child in children:
            if type(child) == str:
                if self.text is None:
                    self.text = child
                else:
                    self.text += child
            else:
                self.append(child)

class div(_html): pass
class p(_html): pass
class h1(_html): pass
class h2(_html): pass
class h3(_html): pass
class h4(_html): pass

class picture(_html): pass
class source(_html): pass

class span(_html): pass
class small(_html): pass
class a(_html): pass
class img(_html): pass
class time(_html): pass
