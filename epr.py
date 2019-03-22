#!/usr/bin/env python3
"""
Usage:
    epr.py [EPUBFILE]

Key binding:
    Help            : ?
    Quit            : q
    Scroll down     : ARROW DOWN    j
    Scroll up       : ARROW UP      k
    Page down       : PGDN          J
    Page up         : PGUP          K
    Next chapter    : ARROW RIGHT   l
    Prev chapter    : ARROW LEFT    h
    Beginning of ch : HOME          g
    End of ch       : END           G
    Shrink          : -
    Enlarge         : =
    TOC             : t
    Metadata        : m

Source:
    https://github.com/wustho/epr.git

"""

import curses
import zipfile
import locale
import sys
import re
import os
import html2text
import json
import xml.etree.ElementTree as ET
from urllib.parse import unquote

locale.setlocale(locale.LC_ALL, "")
# code = locale.getpreferredencoding()

statefile = os.path.join(os.getenv("HOME"), ".epr")
if os.path.exists(statefile):
    with open(statefile, "r") as f:
        state = json.load(f)
else:
    state = {}

# key bindings
SCROLL_DOWN = {curses.KEY_DOWN, ord("j")}
SCROLL_UP = {curses.KEY_UP, ord("k")}
PAGE_DOWN = {curses.KEY_NPAGE, ord("J")}
PAGE_UP = {curses.KEY_PPAGE, ord("K")}
CH_NEXT = {curses.KEY_RIGHT, ord("l")}
CH_PREV = {curses.KEY_LEFT, ord("h")}
CH_HOME = {curses.KEY_HOME, ord("g")}
CH_END = {curses.KEY_END, ord("G")}
SHRINK = ord("-")
WIDEN = ord("=")
META = ord("m")
TOC = ord("t")
FOLLOW = 10
QUIT = {ord("q"), 3}
HELP = {ord("?")}

parser = html2text.HTML2Text()
parser.ignore_emphasis = True
parser.ignore_images = True
parser.re_md_chars_matcher_all = False
parser.skip_internal_links = True

NS = {"DAISY" : "http://www.daisy.org/z3986/2005/ncx/",
      "OPF" : "http://www.idpf.org/2007/opf",
      "CONT" : "urn:oasis:names:tc:opendocument:xmlns:container",
      "XHTML" : "http://www.w3.org/1999/xhtml",
      "EPUB" : "http://www.idpf.org/2007/ops"}

class Epub:
    def __init__(self, fileepub):
        self.path = os.path.abspath(fileepub)
        self.file = zipfile.ZipFile(fileepub, "r")
        cont = ET.parse(self.file.open("META-INF/container.xml"))
        self.rootfile = cont.find("CONT:rootfiles/CONT:rootfile", NS).attrib["full-path"]
        self.rootdir = os.path.dirname(self.rootfile) + "/" if os.path.dirname(self.rootfile) != "" else ""
        cont = ET.parse(self.file.open(self.rootfile))
        # EPUB3
        self.version = cont.getroot().get("version")
        if self.version == "2.0":
            self.toc = self.rootdir + cont.find("OPF:manifest/*[@id='ncx']", NS).get("href")
        elif self.version == "3.0":
            self.toc = self.rootdir + cont.find("OPF:manifest/*[@properties='nav']", NS).get("href")

    def get_meta(self):
        meta = []
        cont = ET.fromstring(self.file.open(self.rootfile).read())
        for i in cont.findall("OPF:metadata/*", NS):
            if i.text != None:
                meta.append([re.sub("{.*?}", "", i.tag), i.text])
        return meta

    def get_contents(self):
        contents = []
        cont = ET.parse(self.file.open(self.rootfile)).getroot()
        manifest = []
        for i in cont.findall("OPF:manifest/*", NS):
            # EPUB3
            if i.get("id") != "ncx" and i.get("properties") != "nav":
                manifest.append([
                    i.get("id"),
                    i.get("href")
                ])
            else:
                toc = self.rootdir + unquote(i.get("href"))

        spine = []
        for i in cont.findall("OPF:spine/*", NS):
            spine.append(i.get("idref"))
        for i in spine:
            for j in manifest:
                if i == j[0]:
                    contents.append(unquote(j[1]))
                    manifest.remove(j)
                    # TODO: test is break necessary
                    break

        namedcontents = []
        toc = ET.parse(self.file.open(toc)).getroot()
        # EPUB3
        if self.version == "2.0":
            navPoints = toc.findall("DAISY:navMap//DAISY:navPoint", NS)
        elif self.version == "3.0":
            navPoints = toc.findall("XHTML:body/XHTML:nav[@EPUB:type='toc']//XHTML:a", NS)
        for i in contents:
            name = "unknown"
            for j in navPoints:
                # EPUB3
                if self.version == "2.0":
                    if i == unquote(j.find("DAISY:content", NS).get("src")):
                        name = j.find("DAISY:navLabel/DAISY:text", NS).text
                        break
                elif self.version == "3.0":
                    if i == unquote(j.get("href")):
                        name = "".join(list(j.itertext()))

            namedcontents.append([
                name,
                self.rootdir + i
            ])

        return namedcontents

def toc(stdscr, ebook, index, width):
    rows, cols = stdscr.getmaxyx()
    hi, wi = rows - 4, cols - 4
    Y, X = 2, 2
    toc = curses.newwin(hi, wi, Y, X)
    toc.box()
    toc.keypad(True)
    toc.addstr(1,2, "Table of Contents")
    toc.addstr(2,2, "-----------------")
    key_toc = 0

    def pad(src, id, top=0):
        pad = curses.newpad(len(src), wi - 2 )
        pad.keypad(True)
        pad.clear()
        for i in range(len(src)):
            if i == id:
                pad.addstr(i, 0, "> " + src[i][0], curses.A_REVERSE)
            else:
                pad.addstr(i, 0, " " + src[i][0])
        # scrolling up
        if top == id and top > 0:
            top = top - 1
        # steady
        elif id - top <= rows - Y -9:
            top = top
        # scrolling down
        else:
            top = id - rows + Y + 9

        pad.refresh(top,0, Y+4,X+4, rows - 5, cols - 6)
        return top

    src = ebook.get_contents()
    toc.refresh()
    top = pad(src, index)

    while key_toc != TOC and key_toc not in QUIT:
        if key_toc in SCROLL_UP and index > 0:
            index -= 1
            top = pad(src, index, top)
        if key_toc in SCROLL_DOWN and index + 1 < len(src):
            index += 1
            top = pad(src, index, top)
        if key_toc == FOLLOW:
            reader(stdscr, ebook, index, width, 0)
        key_toc = toc.getch()

    toc.clear()
    toc.refresh()
    return

def meta(stdscr, ebook):
    rows, cols = stdscr.getmaxyx()
    hi, wi = rows - 4, cols - 4
    Y, X = 2, 2
    meta = curses.newwin(hi, wi, Y, X)
    meta.box()
    meta.keypad(True)
    meta.addstr(1,2, "Metadata")
    meta.addstr(2,2, "--------")
    key_meta = 0

    src = ""
    for i in ebook.get_meta():
        src += html2text.html2text(i[0] + " : " + i[1], bodywidth=wi - 6)
    # src = html2text.html2text(src, wi - 2)
    src_lines = src.split("\n")

    pad = curses.newpad(len(src_lines), wi - 2 )
    pad.keypad(True)
    for i in range(len(src_lines)):
        pad.addstr(i, 0, src_lines[i])
    y = 0
    meta.refresh()
    pad.refresh(y,0, Y+4,X+4, rows - 5, cols - 6)

    while key_meta != META and key_meta not in QUIT:
        if key_meta in SCROLL_UP and y > 0:
            y -= 1
        if key_meta in SCROLL_DOWN and y < len(src_lines) - hi + 4:
            y += 1
        pad.refresh(y,0, 6,5, rows - 5, cols - 5)
        key_meta = meta.getch()

    meta.clear()
    meta.refresh()
    return

def help(stdscr):
    rows, cols = stdscr.getmaxyx()
    hi, wi = rows - 4, cols - 4
    Y, X = 2, 2
    help = curses.newwin(hi, wi, Y, X)
    help.box()
    help.keypad(True)
    help.addstr(1,2, "Help")
    help.addstr(2,2, "----")
    key_help = 0

    src = __doc__
    src_lines = src.split("\n")

    pad = curses.newpad(len(src_lines), wi - 2 )
    pad.keypad(True)
    for i in range(len(src_lines)):
        pad.addstr(i, 0, src_lines[i])
    y = 0
    help.refresh()
    pad.refresh(y,0, Y+4,X+4, rows - 5, cols - 6)

    while key_help not in HELP and key_help not in QUIT:
        if key_help == SCROLL_UP and y > 0:
            y -= 1
        if key_help == SCROLL_DOWN and y < len(src_lines) - hi + 4:
            y += 1
        if key_help == curses.KEY_RESIZE:
            break
        pad.refresh(y,0, 6,5, rows - 5, cols - 5)
        key_help = help.getch()

    help.clear()
    help.refresh()
    return

def reader(stdscr, ebook, index, width, y=0):
    k = 0
    rows, cols = stdscr.getmaxyx()
    x = (cols - width) // 2
    stdscr.clear()
    stdscr.refresh()

    content = ebook.file.open(ebook.get_contents()[index][1]).read()

    parser.body_width = width
    src = parser.handle(content.decode("utf-8"))
    src_lines = src.split("\n")

    pad = curses.newpad(len(src_lines), width + 2) # + 2 unnecessary
    pad.keypad(True)
    for i in range(len(src_lines)):
        pad.addstr(i, 0, src_lines[i])
    pad.addstr(i, width//2 - 10, "-- End of Chapter --", curses.A_REVERSE)
    pad.refresh(y,0, 0,x, rows-1,x+width)

    while True:
        # if k == QUIT or k == 3:
        if k in QUIT:
            for i in state:
                state[i]["lastread"] = str(0)
            state[ebook.path]["lastread"] = str(1)
            state[ebook.path]["index"] = str(index)
            state[ebook.path]["width"] = str(width)
            state[ebook.path]["pos"] = str(y)
            with open(statefile, "w") as f:
                json.dump(state, f, indent=4)
            exit()
        if k in SCROLL_UP:
            if y > 0:
                y -= 1
            # if y == 0 and index > 0:
            #     reader(stdscr, ebook, index-1, width)
        if k in PAGE_UP:
            if y >= rows - 2:
                y -= rows - 2
            else:
                y = 0
        if k in SCROLL_DOWN:
            if y < len(src_lines) - rows:
                y += 1
            # if y + rows >= len(src_lines):
            #     reader(stdscr, ebook, index+1, width)
        if k in PAGE_DOWN:
            if y + rows - 2 <= len(src_lines) - rows:
                y += rows - 2
            else:
                y = len(src_lines) - rows
                if y < 0:
                    y = 0
        if k in CH_NEXT and index < len(ebook.get_contents()) - 1:
            reader(stdscr, ebook, index+1, width)
        if k in CH_PREV and index > 0:
            reader(stdscr, ebook, index-1, width)
        if k in CH_HOME:
            y = 0
        if k in CH_END:
            y = len(src_lines) - rows
        if k == TOC:
            toc(stdscr, ebook, index, width)
        if k == META:
            meta(stdscr, ebook)
        if k in HELP:
            help(stdscr)
        if k == WIDEN and (width + 2) < cols:
            width += 2
            reader(stdscr, ebook, index, width)
            return
        if k == SHRINK and width >= 22:
            width -= 2
            reader(stdscr, ebook, index, width)
            return
        if k == curses.KEY_RESIZE:
            curses.resize_term(rows, cols)
            rows, cols = stdscr.getmaxyx()
            # TODO
            if cols <= width:
                width = cols - 2
            reader(stdscr, ebook, index, width)

        pad.refresh(y,0, 0,x, rows-1,x+width)
        k = pad.getch()

def main(stdscr, file):
    stdscr.keypad(True)
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()
    rows, cols = stdscr.getmaxyx()
    epub = Epub(file)

    if epub.path in state:
        idx = int(state[epub.path]["index"])
        width = int(state[epub.path]["width"])
        y = int(state[epub.path]["pos"])
    else:
        state[epub.path] = {}
        idx = 1
        y = 0
        width = 80

    if cols <= width:
        width = cols - 2
        y = 0
    reader(stdscr, epub, idx, width, y)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        file = False
        for i in state:
            if not os.path.exists(i):
                del state[i]
            elif state[i]["lastread"] == str(1):
                file = i
        if not file:
            print("ERROR: Found no last read file.")
            print(__doc__)
        else:
            curses.wrapper(main, file)
    elif len(sys.argv) == 2 and sys.argv[1] not in ("-h", "--help"):
        curses.wrapper(main, sys.argv[1])
    else:
        print(__doc__)