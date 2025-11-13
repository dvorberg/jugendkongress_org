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
import sys, re, io, traceback, threading, copy
from pathlib import Path
from functools import cached_property

import xml.etree.ElementTree as etree
from flask import g

import markdown
from markdown.extensions import Extension
from markdown.blockprocessors import BlockProcessor

from .. import config, debug
from ..utils import PathSet
from . import macros, html

# https://python-markdown.github.io/extensions/api/#blockprocessors
class FunctionCallProcessor(BlockProcessor):
    """
    My macro call syntax looks (on block level) is

        !macro_name(... parameter list ...)

    With the “!” removed this will be passed Python’s exec()
    directly. To quote the documentation:

        Warning This function executes arbitrary code. Calling it with
        user-supplied input may lead to security vulnerabilities.

    Yeah, that’s what we’re about to do.

    Macros are object that get instantiated in run() below to then be
    called (__call__()) by exec(). Macros have a context supplying
    information provided by view_func().

    Failure is indicated in the log and will be indicated in the output
    HTML as a traceback only in debug mode.
    """

    function_call_re = re.compile(r'''
        (^|\n)         # Start of the block
        !              # The exclamation point
        (?P<name>      # Function name
          \w(\w|\d)*
        )
        \(             # Open parentheses
           (?P<params> # Parameter list
             (
               "(\\"|[^"])*"| # Double quoted strings (with " escaped as \")
               '(\\'|[^'])*'| # Single quoted strings (with ' escaped as \')
               [^"'\)]*       # Any other character that’s not a quote or a )
             )*
           )
        \)             # Close parentheses
    \s*(\n|$)          # End-of-line or end-of-input.
    ''', re.VERBOSE)

    def __init__(self, md, context):
        super().__init__(md.parser)
        self.md = md
        self.context = context

    def test(self, parent: etree.Element, block: str) -> bool:
        """
        Takes two parameters: parent is the parent ElementTree
        element and block is a single, multi-line, Unicode string of
        the current block. test, often a regular expression match,
        returns a true value if the block processor’s run method
        should be called to process starting at that block.
        """
        return self.function_call_re.match(block) is not None

    def run(self, parent: etree.Element, blocks: list[str]) -> None:
        """
        Has the same parent parameter as test; and blocks is the
        list of all remaining blocks in the document, starting with
        the block passed to test. run may return False (not None) to
        signal failure, meaning that it did not process the blocks
        after all. On success, run is expected to pop one or more
        blocks from the front of blocks and attach new nodes to
        parent.
        """
        def report_exception(exc):
            traceback.print_tb(exc.__traceback__, file=sys.stderr)
            traceback.print_exception(exc, file=sys.stderr)

        block = blocks.pop(0)

        # It seems like a huge waste to re.match() here again.
        groups = self.function_call_re.match(block).groupdict()
        function_name = groups["name"]
        params = groups["params"]

        macro_class = getattr(macros, function_name)

        my_globals = globals().copy()
        my_globals["__builtins__"] = __builtins__

        my_locals = { "__retval": None,
                      function_name: macro_class(self.context) }

        try:
            exec(f"__retval = {function_name}({params})",
                 my_globals, my_locals)
            result = my_locals["__retval"]
        except Exception as e:
            print(e, file=sys.stderr)
            if debug:
                raise
            else:
                report_exception(e)
                return

        if result is None:
            return

        if isinstance(result, etree.Element):
            parent.append(result)
            return

        if type(result) == str:
            try:
                parent.append(etree.fromstring(result))
                return
            except Exception as e:
                if debug:
                    raise
                else:
                    report_exception(e)
                    return

        pre = etree.SubElement(parent, "pre")
        pre.text = repr(result)

class FunctionCallExtension(Extension):
    def __init__(self, context):
        self.context = context

    def extendMarkdown(self, md):
        """ Add Admonition to Markdown instance. """
        md.registerExtension(self)

        md.parser.blockprocessors.register(
            FunctionCallProcessor(md, self.context),
            "function_call", 105)

class CiteProcessor(BlockProcessor):
    cite_re = re.compile(r"(^|\n)[–—] (?P<source>.*?)(\n|$)")

    def test(self, parent:etree.Element, block:str) -> bool:
        match = self.cite_re.match(block)
        after_blockquote = (len(parent) > 0 and parent[-1].tag == "blockquote")
        return (match is not None and after_blockquote)

    def run(self, parent:etree.Element, blocks:list[str]) -> None:
        block = blocks.pop(0)
        groups = self.cite_re.match(block).groupdict()

        blockquote = parent[-1]
        del parent[-1]
        blockquote.set("class", "blockquote")

        parent.append(html.figure(blockquote,
                                  html.figcaption(groups["source"],
                                                  class_="blockquote-footer")))

class CiteExtension(Extension):
    def extendMarkdown(self, md):
        """ Add Admonition to Markdown instance. """
        md.registerExtension(self)
        md.parser.blockprocessors.register(
            CiteProcessor(md.parser), "cite", 105)

class MarkdownResult(object):
    def __init__(self, source:str, context:macros.MacroContext):
        context.result = self

        self.md = markdown.Markdown(
            extensions=["extra", "meta", "nl2br",
                        FunctionCallExtension(context),
                        CiteExtension()])

        self.md.treeprocessors.deregister("prettify")
        self._original_serializer = self.md.serializer
        self.md.serializer = self._serializer

        self._source = source

    def convert(self):
        self.md.convert(self._source)

    def _serializer(self, root_element:etree.Element):
        self._root_element = copy.deepcopy(root_element)
        return "<div />"

    def get_meta(self, name, default="", as_list=False):
        l = self.md.Meta.get(name, [])
        if len(l) == 0:
            if as_list:
                return []
            else:
                return default
        if len(l) == 1 and (not as_list):
            return l[0]
        else:
            return l

    @cached_property
    def html(self):
        # We have aborted markdown.code.Markdown.convert() by returning
        # an empty string above. We now perform the remainder of convert()’s
        # job:
        # - running the actual serializer
        # - stripping the doc_tag
        # - running the post processors.
        html = self._original_serializer(self._root_element)
        start = f"<{self.md.doc_tag}>"
        end = f"</{self.md.doc_tag}>"

        if html.startswith(start) and html.endswith(end):
            html = html[len(start):-len(end)]
        elif html == f"<{self.md.doc_tag} />":
            # Empty document
            html = ""

        # Run the text post-processors.
        # I didn’t design this.
        for pp in self.md.postprocessors:
            html = pp.run(html)

        return html.strip()

    @property
    def root_element(self) -> etree.Element:
        return self._root_element

    def __str__(self):
        return self.html

class NeverMatch(object):
    def __eq__(self):
        return False

class CacheEntry(object):
    def __init__(self, paths:set, result:MarkdownResult):
        if debug:
            # In development mode, we make sure all the paths are absolute
            # paths.
            for path in paths:
                if not path.is_absolute:
                    raise ValueError("All paths must be absolute.")

        self.paths = paths
        self.result = result
        self.ctime = self.mtime

    @property
    def mtime(self):
        """
        Return the time of the youngest modification in the file set.
        """
        try:
            return max([ path.stat().st_mtime for path in self.paths ])
        except FileNotFoundError:
            return NeverMatch()

    @property
    def valid(self):
        """
        A cache entry is valid if the ctime (creation time) is equal to
        the mtime (modification time).
        """
        return self.ctime == self.mtime

    @property
    def html(self):
        return self.result.html

    def register_dependent_files(self, *paths):
        for path in paths:
            self.paths.add(path)

markdown_cache_lock = threading.Lock()
class MarkdownCache(object):
    def __init__(self):
        self._cache = {}

    def get_or_render(self, abspath:Path, force_render=False):
        with markdown_cache_lock:
            if ( force_render
                 or abspath not in self._cache
                 or (not self._cache[abspath].valid)
                ):
                paths = PathSet(abspath)
                result = MarkdownResult(
                    abspath.open().read(),
                    macros.MacroContext(
                        markdown_file_path=abspath,
                        pathset=paths))

                result.convert()

                self._cache[abspath] = CacheEntry(paths, result)

        return self._cache[abspath].result

markdown_cache = MarkdownCache()

def view_func(infile_path:str):
    infile_path = Path(infile_path)
    www_root = Path(config["WWW_PATH"])

    abspath = Path(www_root, infile_path)
    result = markdown_cache.get_or_render(abspath)
    template = g.skin.load_template("skin/jugendkongress/markdown_view.pt")
    return template(html=result.html)
