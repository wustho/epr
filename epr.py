#!/usr/bin/env python3
"""\
Usages:
    epr             read last epub
    epr EPUBFILE    read EPUBFILE
    epr STRINGS     read matched STRINGS from history
    epr NUMBER      read file from history
                    with associated NUMBER

Options:
    -r              print reading history
    -d              dump epub
    -h, --help      print short, long help

Key Binding:
    Help            : ?
    Quit            : q
    Scroll down     : DOWN      j
    Scroll up       : UP        k
    Page down       : PGDN      RIGHT   SPC
    Page up         : PGUP      LEFT
    Next chapter    : n
    Prev chapter    : p
    Beginning of ch : HOME      g
    End of ch       : END       G
    Open image      : o
    Search          : /
    Next Occurence  : n
    Prev Occurence  : N
    Shrink          : -
    Enlarge         : =
    Toggle width    : 0
    ToC             : TAB       t
    Metadata        : m
"""

__version__ = "2.2.10"
__license__ = "MIT"
__author__ = "Benawi Adha"
__url__ = "https://github.com/wustho/epr"

import curses
import zipfile
import sys
import re
import os
import textwrap
import json
import tempfile
import shutil
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from html import unescape
from subprocess import run
from html.parser import HTMLParser
from difflib import SequenceMatcher as SM

# key bindings
SCROLL_DOWN = {curses.KEY_DOWN, ord("j")}
SCROLL_UP = {curses.KEY_UP, ord("k")}
PAGE_DOWN = {curses.KEY_NPAGE, ord("l"), ord(" "), curses.KEY_RIGHT}
PAGE_UP = {curses.KEY_PPAGE, ord("h"), curses.KEY_LEFT}
CH_NEXT = {ord("n")}
CH_PREV = {ord("p")}
CH_HOME = {curses.KEY_HOME, ord("g")}
CH_END = {curses.KEY_END, ord("G")}
SHRINK = ord("-")
WIDEN = ord("=")
META = ord("m")
TOC = {9, ord("\t"), ord("t")}
FOLLOW = {10}
QUIT = {ord("q"), 3, 27}
HELP = {ord("?")}

if os.getenv("HOME") is not None:
    statefile = os.path.join(os.getenv("HOME"), ".epr")
    if os.path.isdir(os.path.join(os.getenv("HOME"), ".config")):
        configdir = os.path.join(os.getenv("HOME"), ".config", "epr")
        os.makedirs(configdir, exist_ok=True)
        if os.path.isfile(statefile):
            if os.path.isfile(os.path.join(configdir, "config")):
                os.remove(os.path.join(configdir, "config"))
            shutil.move(statefile, os.path.join(configdir, "config"))
        statefile = os.path.join(configdir, "config")
elif os.getenv("USERPROFILE") is not None:
    statefile = os.path.join(os.getenv("USERPROFILE"), ".epr")
else:
    statefile = os.devnull

if os.path.exists(statefile):
    with open(statefile, "r") as f:
        state = json.load(f)
else:
    state = {}

NS = {"DAISY": "http://www.daisy.org/z3986/2005/ncx/",
      "OPF": "http://www.idpf.org/2007/opf",
      "CONT": "urn:oasis:names:tc:opendocument:xmlns:container",
      "XHTML": "http://www.w3.org/1999/xhtml",
      "EPUB": "http://www.idpf.org/2007/ops"}

LINEPRSRV = 0  # default = 2

SEARCHPATTERN = None

VWR_LIST = [
    "feh",
    "gnome-open",
    "gvfs-open",
    "xdg-open",
    "kde-open",
    "firefox"
]
VWR = None
if sys.platform == "win32":
    VWR = "start"
else:
    for i in VWR_LIST:
        if shutil.which(i) is not None:
            VWR = i
            break

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
            # self.toc = self.rootdir + cont.find("OPF:manifest/*[@id='ncx']", NS).get("href")
            self.toc = self.rootdir + cont.find("OPF:manifest/*[@media-type='application/x-dtbncx+xml']", NS).get("href")
        elif self.version == "3.0":
            self.toc = self.rootdir + cont.find("OPF:manifest/*[@properties='nav']", NS).get("href")

        self.contents = []
        self.toc_entries = []

    def get_meta(self):
        meta = []
        # why self.file.read(self.rootfile) problematic
        cont = ET.fromstring(self.file.open(self.rootfile).read())
        for i in cont.findall("OPF:metadata/*", NS):
            if i.text is not None:
                meta.append([re.sub("{.*?}", "", i.tag), i.text])
        return meta

    def initialize(self):
        cont = ET.parse(self.file.open(self.rootfile)).getroot()
        manifest = []
        for i in cont.findall("OPF:manifest/*", NS):
            # EPUB3
            # if i.get("id") != "ncx" and i.get("properties") != "nav":
            if i.get("media-type") != "application/x-dtbncx+xml" and i.get("properties") != "nav":
                manifest.append([
                    i.get("id"),
                    i.get("href")
                ])

        spine, contents = [], []
        for i in cont.findall("OPF:spine/*", NS):
            spine.append(i.get("idref"))
        for i in spine:
            for j in manifest:
                if i == j[0]:
                    self.contents.append(self.rootdir+unquote(j[1]))
                    contents.append(unquote(j[1]))
                    manifest.remove(j)
                    # TODO: test is break necessary
                    break

        toc = ET.parse(self.file.open(self.toc)).getroot()
        # EPUB3
        if self.version == "2.0":
            navPoints = toc.findall("DAISY:navMap//DAISY:navPoint", NS)
        elif self.version == "3.0":
            navPoints = toc.findall("XHTML:body//XHTML:nav[@EPUB:type='toc']//XHTML:a", NS)
        for i in contents:
            name = "-"
            for j in navPoints:
                # EPUB3
                if self.version == "2.0":
                    # if i == unquote(j.find("DAISY:content", NS).get("src")):
                    if re.search(i, unquote(j.find("DAISY:content", NS).get("src"))) is not None:
                        name = j.find("DAISY:navLabel/DAISY:text", NS).text
                        break
                elif self.version == "3.0":
                    # if i == unquote(j.get("href")):
                    if re.search(i, unquote(j.get("href"))) is not None:
                        name = "".join(list(j.itertext()))
                        break
            self.toc_entries.append(name)

class HTMLtoLines(HTMLParser):
    para = {"p", "div"}
    inde = {"q", "dt", "dd", "blockquote", "pre"}
    bull = {"li"}
    hide = {"script", "style", "head"}
    # hide = {"script", "style", "head", ", "sub}

    def __init__(self):
        HTMLParser.__init__(self)
        self.text = [""]
        self.imgs = []
        self.ishead = False
        self.isinde = False
        self.isbull = False
        self.ishidden = False
        self.idhead = set()
        self.idinde = set()
        self.idbull = set()

    def handle_starttag(self, tag, attrs):
        if re.match("h[1-6]", tag) is not None:
            self.ishead = True
        elif tag in self.inde:
            self.isinde = True
        elif tag in self.bull:
            self.isbull = True
        elif tag in self.hide:
            self.ishidden = True
        elif tag == "sup":
            self.text[-1] += "^{"
        elif tag == "sub":
            self.text[-1] += "_{"
        elif tag == "image":
            for i in attrs:
                if i[0] == "xlink:href":
                    self.text.append("[IMG:{}]".format(len(self.imgs)))
                    self.imgs.append(unquote(i[1]))

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.text += [""]
        elif tag in {"img", "image"}:
            for i in attrs:
                if (tag == "img" and i[0] == "src") or (tag == "image" and i[0] == "xlink:href"):
                    self.text.append("[IMG:{}]".format(len(self.imgs)))
                    self.imgs.append(unquote(i[1]))
                    self.text.append("")

    def handle_endtag(self, tag):
        if re.match("h[1-6]", tag) is not None:
            self.text.append("")
            self.text.append("")
            self.ishead = False
        elif tag in self.para:
            self.text.append("")
        elif tag in self.hide:
            self.ishidden = False
        elif tag in self.inde:
            if self.text[-1] != "":
                self.text.append("")
            self.isinde = False
        elif tag in self.bull:
            if self.text[-1] != "":
                self.text.append("")
            self.isbull = False
        elif tag in {"sub", "sup"}:
            self.text[-1] += "}"
        elif tag == "image":
            self.text.append("")

    def handle_data(self, raw):
        if raw and not self.ishidden:
            if self.text[-1] == "":
                tmp = raw.lstrip()
            else:
                tmp = raw
            line = unescape(re.sub(r"\s+", " ", tmp))
            self.text[-1] += line
            if self.ishead:
                self.idhead.add(len(self.text)-1)
            elif self.isbull:
                self.idbull.add(len(self.text)-1)
            elif self.isinde:
                self.idinde.add(len(self.text)-1)

    def get_lines(self, width=0):
        text = []
        if width == 0:
            return self.text
        for n, i in enumerate(self.text):
            if n in self.idhead:
                text += [i.rjust(width//2 + len(i)//2)] + [""]
            elif n in self.idinde:
                text += ["   "+j for j in textwrap.fill(i, width - 3).splitlines()] + [""]
            elif n in self.idbull:
                tmp = textwrap.fill(i, width - 3).splitlines()
                text += [" - "+j if j == tmp[0] else "   "+j for j in tmp] + [""]
            else:
                text += textwrap.fill(i, width).splitlines() + [""]
        return text, self.imgs

def savestate(file, index, width, pos, pctg ):
    for i in state:
        state[i]["lastread"] = str(0)
    state[file]["lastread"] = str(1)
    state[file]["index"] = str(index)
    state[file]["width"] = str(width)
    state[file]["pos"] = str(pos)
    state[file]["pctg"] = str(pctg)
    with open(statefile, "w") as f:
        json.dump(state, f, indent=4)

def pgup(pos, winhi, preservedline=0):
    if pos >= winhi - preservedline:
        return pos - winhi + preservedline
    else:
        return 0

def pgdn(pos, tot, winhi, preservedline=0):
    if pos + winhi <= tot - winhi:
        return pos + winhi
    else:
        pos = tot - winhi
        if pos < 0:
            return 0
        return pos

def pgend(tot, winhi):
    if tot - winhi >= 0:
        return tot - winhi
    else:
        return 0

def toc(stdscr, src, index, width):
    rows, cols = stdscr.getmaxyx()
    hi, wi = rows - 4, cols - 4
    Y, X = 2, 2
    oldindex = index
    toc = curses.newwin(hi, wi, Y, X)
    toc.box()
    toc.keypad(True)
    toc.addstr(1,2, "Table of Contents")
    toc.addstr(2,2, "-----------------")
    key_toc = 0

    totlines = len(src)
    toc.refresh()
    pad = curses.newpad(totlines, wi - 2 )
    pad.keypad(True)

    padhi = rows - 5 - Y - 4 + 1
    y = 0
    if index in range(padhi//2, totlines - padhi//2):
        y = index - padhi//2 + 1
    d = len(str(totlines))
    span = []

    for n, i in enumerate(src):
        # strs = "  " + str(n+1).rjust(d) + " " + i[0]
        strs = "  " + i
        strs = strs[0:wi-3]
        pad.addstr(n, 0, strs)
        span.append(len(strs))

    while key_toc not in TOC and key_toc not in QUIT:
        if key_toc in SCROLL_UP and index > 0:
            index -= 1
        elif key_toc in SCROLL_DOWN and index + 1 < totlines:
            index += 1
        elif key_toc in FOLLOW:
            if index == oldindex:
                break
            return index
        elif key_toc in PAGE_UP:
            index -= 3
            if index < 0:
                index = 0
        elif key_toc in PAGE_DOWN:
            index += 3
            if index >= totlines:
                index = totlines - 1
        elif key_toc in CH_HOME:
            index = 0
        elif key_toc in CH_END:
            index = totlines - 1
        elif key_toc == curses.KEY_RESIZE:
            return key_toc

        while index not in range(y, y+padhi):
            if index < y:
                y -= 1
            else:
                y += 1

        for n in range(totlines):
            att = curses.A_REVERSE if index == n else curses.A_NORMAL
            pre = ">>" if index == n else "  "
            pad.addstr(n, 0, pre)
            pad.chgat(n, 0, span[n], att)

        pad.refresh(y, 0, Y+4,X+4, rows - 5, cols - 6)
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

    mdata = []
    for i in ebook.get_meta():
        data = re.sub("<[^>]*>", "", i[1])
        data = re.sub("\t", "", data)
        mdata += textwrap.fill(i[0].upper() + ": " + data, wi - 6).splitlines()
    src_lines = mdata
    totlines = len(src_lines)

    pad = curses.newpad(totlines, wi - 2 )
    pad.keypad(True)
    for n, i in enumerate(src_lines):
        pad.addstr(n, 0, i)
    y = 0
    meta.refresh()
    pad.refresh(y,0, Y+4,X+4, rows - 5, cols - 6)

    padhi = rows - 5 - Y - 4 + 1

    while key_meta != META and key_meta not in QUIT:
        if key_meta in SCROLL_UP and y > 0:
            y -= 1
        elif key_meta in SCROLL_DOWN and y < totlines - hi + 6:
            y += 1
        elif key_meta in PAGE_UP:
            y = pgup(y, padhi)
        elif key_meta in PAGE_DOWN:
            y = pgdn(y, totlines, padhi)
        elif key_meta in CH_HOME:
            y = 0
        elif key_meta in CH_END:
            y = pgend(totlines, padhi)
        elif key_meta == curses.KEY_RESIZE:
            return key_meta
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

    src = re.search("Key Bind(\n|.)*", __doc__).group()
    src_lines = src.splitlines()
    totlines = len(src_lines)

    pad = curses.newpad(totlines, wi - 2 )
    pad.keypad(True)
    for n, i in enumerate(src_lines):
        pad.addstr(n, 0, i)
    y = 0
    help.refresh()
    pad.refresh(y,0, Y+4,X+4, rows - 5, cols - 6)

    padhi = rows - 5 - Y - 4 + 1

    while key_help not in HELP and key_help not in QUIT:
        if key_help in SCROLL_UP and y > 0:
            y -= 1
        elif key_help in SCROLL_DOWN and y < totlines - hi + 6:
            y += 1
        elif key_help in PAGE_UP:
            y = pgup(y, padhi)
        elif key_help in PAGE_DOWN:
            y = pgdn(y, totlines, padhi)
        elif key_help in CH_HOME:
            y = 0
        elif key_help in CH_END:
            y = pgend(totlines, padhi)
        elif key_help == curses.KEY_RESIZE:
            return key_help
        pad.refresh(y,0, 6,5, rows - 5, cols - 5)
        key_help = help.getch()

    help.clear()
    help.refresh()
    return

def dots_path(curr, tofi):
    candir = curr.split("/")
    tofi = tofi.split("/")
    alld = tofi.count("..")
    t = len(candir)
    candir = candir[0:t-alld-1]
    try:
        while True:
            tofi.remove("..")
    except ValueError:
        pass
    return "/".join(candir+tofi)

def open_media(scr, epub, src):
    sfx = os.path.splitext(src)[1]
    fd, path = tempfile.mkstemp(suffix=sfx)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(epub.file.read(src))
        run(VWR +" "+ path, shell=True)
        k = scr.getch()
    finally:
        os.remove(path)
    return k

def searching(stdscr, pad, src, width, y, ch, tot):
    global SEARCHPATTERN
    rows, cols = stdscr.getmaxyx()
    x = (cols - width) // 2
    if SEARCHPATTERN is None:
        stat = curses.newwin(1, cols, rows-1, 0)
        stat.keypad(True)
        curses.echo(1)
        curses.curs_set(1)
        SEARCHPATTERN = ""
        stat.addstr(0, 0, " Regex:", curses.A_REVERSE)
        stat.addstr(0, 7, SEARCHPATTERN)
        stat.refresh()
        while True:
            ipt = stat.getch()
            if ipt == 27:
                stat.clear()
                stat.refresh()
                curses.echo(0)
                curses.curs_set(0)
                SEARCHPATTERN = None
                return y
            elif ipt == 10:
                SEARCHPATTERN = "/"+SEARCHPATTERN
                stat.clear()
                stat.refresh()
                curses.echo(0)
                curses.curs_set(0)
                break
            # TODO: why different behaviour unix dos or win lin
            elif ipt in {8, curses.KEY_BACKSPACE}:
                SEARCHPATTERN = SEARCHPATTERN[:-1]
            elif ipt == curses.KEY_RESIZE:
                stat.clear()
                stat.refresh()
                curses.echo(0)
                curses.curs_set(0)
                SEARCHPATTERN = None
                return curses.KEY_RESIZE
            else:
                SEARCHPATTERN += chr(ipt)

            stat.clear()
            stat.addstr(0, 0, " Regex:", curses.A_REVERSE)
            stat.addstr(0, 7, SEARCHPATTERN)
            stat.refresh()

    if SEARCHPATTERN in {"?", "/"}:
        SEARCHPATTERN = None
        return y

    found = []
    pattern = re.compile(SEARCHPATTERN[1:], re.IGNORECASE)
    for n, i in enumerate(src):
        for j in pattern.finditer(i):
            found.append([n, j.span()[0], j.span()[1] - j.span()[0]])

    if found == []:
        if SEARCHPATTERN[0] == "/" and ch + 1 < tot:
            return 1
        elif SEARCHPATTERN[0] == "?" and ch > 0:
            return -1
        else:
            s = 0
            while True:
                if s in QUIT:
                    SEARCHPATTERN = None
                    stdscr.clear()
                    stdscr.refresh()
                    return y
                elif s == ord("n") and ch == 0:
                    SEARCHPATTERN = "/"+SEARCHPATTERN[1:]
                    return 1
                elif s == ord("N") and ch +1 == tot:
                    SEARCHPATTERN = "?"+SEARCHPATTERN[1:]
                    return -1

                stdscr.clear()
                stdscr.addstr(rows-1, 0, " Finished searching: " + SEARCHPATTERN[1:] + " ", curses.A_REVERSE)
                stdscr.refresh()
                pad.refresh(y,0, 0,x, rows-2,x+width)
                s = pad.getch()

    sidx = len(found) - 1
    if SEARCHPATTERN[0] == "/":
        if y > found[-1][0]:
            return 1
        for n, i in enumerate(found):
            if i[0] >= y:
                sidx = n
                break

    s = 0
    msg = " Searching: " + SEARCHPATTERN[1:] + " --- Res {}/{} Ch {}/{} ".format(
        sidx + 1,
        len(found),
        ch+1, tot)
    while True:
        if s in QUIT:
            SEARCHPATTERN = None
            for i in found:
                pad.chgat(i[0], i[1], i[2], curses.A_NORMAL)
            stdscr.clear()
            stdscr.refresh()
            return y
        elif s == ord("n"):
            SEARCHPATTERN = "/"+SEARCHPATTERN[1:]
            if sidx == len(found) - 1:
                if ch + 1 < tot:
                    return 1
                else:
                    s = 0
                    msg = " Finished searching: " + SEARCHPATTERN[1:] + " "
                    continue
            else:
                sidx += 1
                msg = " Searching: " + SEARCHPATTERN[1:] + " --- Res {}/{} Ch {}/{} ".format(
                    sidx + 1,
                    len(found),
                    ch+1, tot)
        elif s == ord("N"):
            SEARCHPATTERN = "?"+SEARCHPATTERN[1:]
            if sidx == 0:
                if ch > 0:
                    return -1
                else:
                    s = 0
                    msg = " Finished searching: " + SEARCHPATTERN[1:] + " "
                    continue
            else:
                sidx -= 1
                msg = " Searching: " + SEARCHPATTERN[1:] + " --- Res {}/{} Ch {}/{} ".format(
                    sidx + 1,
                    len(found),
                    ch+1, tot)
        elif s == curses.KEY_RESIZE:
            return s

        while found[sidx][0] not in list(range(y, y+rows-1)):
            if found[sidx][0] > y:
                y += rows - 1
            else:
                y -= rows - 1
                if y < 0:
                    y = 0

        for n, i in enumerate(found):
            attr = curses.A_REVERSE if n == sidx else curses.A_NORMAL
            pad.chgat(i[0], i[1], i[2], attr)

        stdscr.clear()
        stdscr.addstr(rows-1, 0, msg, curses.A_REVERSE)
        stdscr.refresh()
        pad.refresh(y,0, 0,x, rows-2,x+width)
        s = pad.getch()

def reader(stdscr, ebook, index, width, y, pctg):
    k = 0 if SEARCHPATTERN is None else ord("/")
    rows, cols = stdscr.getmaxyx()
    x = (cols - width) // 2

    contents = ebook.contents
    toc_src = ebook.toc_entries
    chpath = contents[index]
    content = ebook.file.open(chpath).read()
    content = content.decode("utf-8")

    parser = HTMLtoLines()
    try:
        parser.feed(content)
        parser.close()
    except:
        pass

    src_lines, imgs = parser.get_lines(width)
    totlines = len(src_lines)

    if y < 0 and totlines <= rows:
        y = 0
    elif pctg is not None:
        y = round(pctg*totlines)
    else:
        y = y % totlines

    pad = curses.newpad(totlines, width + 2) # + 2 unnecessary
    pad.keypad(True)
    for n, i in enumerate(src_lines):
        if re.search("\[IMG:[0-9]+\]", i):
            pad.addstr(n, width//2 - len(i)//2, i, curses.A_REVERSE)
        else:
            pad.addstr(n, 0, i)
    if index == 0:
        suff = "     End --> "
    elif index == len(contents) - 1:
        suff = " <-- End     "
    else:
        suff = " <-- End --> "
    pad.addstr(n, width//2 - 7, suff, curses.A_REVERSE)

    stdscr.clear()
    stdscr.refresh()
    pad.refresh(y,0, 0,x, rows-1,x+width)

    while True:
        if k in QUIT:
            savestate(ebook.path, index, width, y, y/totlines)
            sys.exit()
        elif k in SCROLL_UP:
            if y > 0:
                y -= 1
            elif index != 0:
                return -1, width, -rows, None
        elif k in PAGE_UP:
            if y == 0 and index != 0:
                return -1, width, -rows, None
            else:
                y = pgup(y, rows, LINEPRSRV)
        elif k in SCROLL_DOWN:
            if y < totlines - rows:
                y += 1
            elif index != len(contents)-1:
                return 1, width, 0, None
        elif k in PAGE_DOWN:
            if totlines - y - LINEPRSRV > rows:
                y += rows - LINEPRSRV
            elif index != len(contents)-1:
                return 1, width, 0, None
        elif k in CH_NEXT and index < len(contents) - 1:
            return 1, width, 0, None
        elif k in CH_PREV and index > 0:
            return -1, width, 0, None
        elif k in CH_HOME:
            y = 0
        elif k in CH_END:
            y = pgend(totlines, rows)
        elif k in TOC:
            fllwd = toc(stdscr, toc_src, index, width)
            if fllwd is not None:
                if fllwd == curses.KEY_RESIZE:
                    k = fllwd
                    continue
                return fllwd - index, width, 0, None
        elif k == META:
            k = meta(stdscr, ebook)
            if k == curses.KEY_RESIZE:
                continue
        elif k in HELP:
            k = help(stdscr)
            if k == curses.KEY_RESIZE:
                continue
        elif k == WIDEN and (width + 2) < cols:
            width += 2
            return 0, width, 0, y/totlines
        elif k == SHRINK and width >= 22:
            width -= 2
            return 0, width, 0, y/totlines
        elif k == ord("0"):
            if width != 80 and cols - 2 >= 80:
                return 0, 80, 0, y/totlines
            else:
                return 0, cols - 2, 0, y/totlines
        elif k == ord("/"):
            fs = searching(stdscr, pad, src_lines, width, y, index, len(contents))
            if fs == curses.KEY_RESIZE:
                k = fs
                continue
            elif SEARCHPATTERN is not None:
                return fs, width, 0, None
            else:
                y = fs
        elif k == ord("o") and VWR is not None:
            gambar, idx = [], []
            for n, i in enumerate(src_lines[y:y+rows]):
                img = re.search("(?<=\[IMG:)[0-9]+(?=\])", i)
                if img is not None:
                    gambar.append(img.group())
                    idx.append(n)

            impath = ""
            if len(gambar) == 1:
                impath = imgs[int(gambar[0])]
            elif len(gambar) > 1:
                p, i = 0, 0
                while p not in QUIT and p not in FOLLOW:
                    stdscr.move(idx[i], x + width//2 + len(gambar[i]) + 1)
                    stdscr.refresh()
                    curses.curs_set(1)
                    p = pad.getch()
                    if p in SCROLL_DOWN:
                        i += 1
                    elif p in SCROLL_UP:
                        i -= 1
                    i = i % len(gambar)

                curses.curs_set(0)
                if p in FOLLOW:
                    impath = imgs[int(gambar[i])]

            if impath != "":
                imgsrc = dots_path(chpath, impath)
                k = open_media(pad, ebook, imgsrc)
                continue
        elif k == curses.KEY_RESIZE:
            savestate(ebook.path, index, width, y, y/totlines)
            # stated in pypi windows-curses page:
            # to call resize_term right after KEY_RESIZE
            if sys.platform == "win32":
                curses.resize_term(rows, cols)
                rows, cols = stdscr.getmaxyx()
            else:
                rows, cols = stdscr.getmaxyx()
                curses.resize_term(rows, cols)
            if cols <= width:
                return 0, cols - 2, 0, y/totlines
            else:
                return 0, width, y, None

        try:
            stdscr.clear()
            stdscr.refresh()
            if totlines - y < rows:
                pad.refresh(y,0, 0,x, totlines-y,x+width)
            else:
                pad.refresh(y,0, 0,x, rows-1,x+width)
        except curses.error:
            pass
        k = pad.getch()

def preread(stdscr, file):
    curses.use_default_colors()
    stdscr.keypad(True)
    curses.curs_set(0)
    stdscr.clear()
    rows, cols = stdscr.getmaxyx()
    stdscr.addstr(rows-1,0, "Loading...")
    stdscr.refresh()

    epub = Epub(file)

    if epub.path in state:
        idx = int(state[epub.path]["index"])
        width = int(state[epub.path]["width"])
        y = int(state[epub.path]["pos"])
        pctg = None
    else:
        state[epub.path] = {}
        idx = 0
        y = 0
        width = 80
        pctg = None

    if cols <= width:
        width = cols - 2
        if "pctg" in state[epub.path]:
            pctg = float(state[epub.path]["pctg"])

    epub.initialize()

    while True:
        incr, width, y, pctg = reader(stdscr, epub, idx, width, y, pctg)
        idx += incr

def main():
    args = []
    if sys.argv[1:] != []:
        args += sys.argv[1:]

    if len({"-h", "--help"} & set(args)) != 0:
        hlp = __doc__.rstrip()
        if "-h" in args:
            hlp = re.search("(\n|.)*(?=\n\nKey)", hlp).group()
        print(hlp)
        sys.exit()

    if len({"-v", "--version", "-V"} & set(args)) != 0:
        print(__version__)
        print(__license__, "License")
        print("Copyright (c) 2019", __author__)
        print(__url__)
        sys.exit()

    if len({"-d"} & set(args)) != 0:
        args.remove("-d")
        dump = True
    else:
        dump = False

    if args == []:
        file, todel = False, []
        for i in state:
            if not os.path.exists(i):
                todel.append(i)
            elif state[i]["lastread"] == str(1):
                file = i

        for i in todel:
            del state[i]

        if not file:
            print(__doc__)
            sys.exit("ERROR: Found no last read file.")

    elif os.path.isfile(args[0]):
        file = args[0]

    else:
        val = cand = 0
        todel = []
        for i in state.keys():
            if not os.path.exists(i):
                todel.append(i)
            else:
                match_val = sum([j.size for j in SM(None, i.lower(), " ".join(args).lower()).get_matching_blocks()])
                if match_val >= val:
                    val = match_val
                    cand = i
        for i in todel:
            del state[i]
        with open(statefile, "w") as f:
            json.dump(state, f, indent=4)
        if len(args) == 1 and re.match(r"[0-9]+", args[0]) is not None:
            try:
                cand = list(state.keys())[int(args[0])-1]
                val = 1
            except IndexError:
                val = 0
        if val != 0 and len({"-r"} & set(args)) == 0:
            file = cand
        else:
            print("\nReading history:")
            dig = len(str(len(state.keys())+1))
            for n, i in enumerate(state.keys()):
                print(str(n+1).rjust(dig) + ("* " if state[i]["lastread"] == "1" else "  ") + i)
            if len({"-r"} & set(args)) != 0:
                sys.exit()
            else:
                print()
                sys.exit("ERROR: Found no matching history.")

    if dump:
        epub = Epub(file)
        epub.initialize()
        for i in epub.contents:
            content = epub.file.open(i).read()
            content = content.decode("utf-8")
            parser = HTMLtoLines()
            try:
                parser.feed(content)
                parser.close()
            except:
                pass
            src_lines = parser.get_lines()
            # sys.stdout.reconfigure(encoding="utf-8")  # Python>=3.7
            for j in src_lines:
                sys.stdout.buffer.write((j+"\n\n").encode("utf-8"))
        sys.exit()

    else:
        curses.wrapper(preread, file)

if __name__ == "__main__":
    main()
