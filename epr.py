#!/usr/bin/env python3
"""\
Usages:
    epr             read last epub
    epr EPUBFILE    read EPUBFILE
    epr STRINGS     read matched STRINGS from history

Options:
    -r              print reading history
    -d              dump epub
    -h, --help      print short/long help

Key Binding:
    Help            : ?
    Quit            : q
    Scroll down     : DOWN      j
    Scroll up       : UP        k
    Page down       : PGDN      J   SPC
    Page up         : PGUP      K
    Next chapter    : RIGHT     l
    Prev chapter    : LEFT      h
    Beginning of ch : HOME      g
    End of ch       : END       G
    Open image      : o
    Search          : /
    Next Occurence  : n
    Prev Occurence  : N
    Shrink          : -
    Enlarge         : =
    TOC             : t
    Metadata        : m

v2.1.3-md
MIT License
Copyright (c) 2019 Benawi Adha
https://github.com/wustho/epr
"""

import curses
import zipfile
import sys
import re
import os
import textwrap
import json
import tempfile
import shutil
import html2text
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from subprocess import run
from difflib import SequenceMatcher as SM

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

# key bindings
SCROLL_DOWN = {curses.KEY_DOWN, ord("j")}
SCROLL_UP = {curses.KEY_UP, ord("k")}
PAGE_DOWN = {curses.KEY_NPAGE, ord("J"), ord(" ")}
PAGE_UP = {curses.KEY_PPAGE, ord("K")}
CH_NEXT = {curses.KEY_RIGHT, ord("l")}
CH_PREV = {curses.KEY_LEFT, ord("h")}
CH_HOME = {curses.KEY_HOME, ord("g")}
CH_END = {curses.KEY_END, ord("G")}
SHRINK = ord("-")
WIDEN = ord("=")
META = ord("m")
TOC = ord("t")
FOLLOW = {10}
QUIT = {ord("q"), 3, 27}
HELP = {ord("?")}

NS = {"DAISY": "http://www.daisy.org/z3986/2005/ncx/",
      "OPF": "http://www.idpf.org/2007/opf",
      "CONT": "urn:oasis:names:tc:opendocument:xmlns:container",
      "XHTML": "http://www.w3.org/1999/xhtml",
      "EPUB": "http://www.idpf.org/2007/ops"}

RIGHTPADDING = 0  # default = 2
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

parser = html2text.HTML2Text()
parser.ignore_emphasis = False  # True
parser.ignore_images = False
parser.re_md_chars_matcher_all = False
parser.skip_internal_links = False  # True
parser.ignore_links = False  # True

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

    def get_meta(self):
        meta = []
        # why self.file.read(self.rootfile) problematic
        cont = ET.fromstring(self.file.open(self.rootfile).read())
        for i in cont.findall("OPF:metadata/*", NS):
            if i.text is not None:
                meta.append([re.sub("{.*?}", "", i.tag), i.text])
        return meta

    def get_contents(self):
        contents = []
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
            navPoints = toc.findall("XHTML:body//XHTML:nav[@EPUB:type='toc']//XHTML:a", NS)
        for i in contents:
            name = "unknown"
            for j in navPoints:
                # EPUB3
                if self.version == "2.0":
                    # if i == unquote(j.find("DAISY:content", NS).get("src")):
                    if re.search(i, unquote(j.find("DAISY:content", NS).get("src"))) is not None:
                        name = j.find("DAISY:navLabel/DAISY:text", NS).text
                        break
                elif self.version == "3.0":
                    if i == unquote(j.get("href")):
                        name = "".join(list(j.itertext()))
                        break

            namedcontents.append([
                name,
                self.rootdir + i
            ])

        return namedcontents

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

def toc(stdscr, ebook, index, width):
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

    src = ebook.get_contents()
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
        strs = "  " + str(n+1).rjust(d) + " " + i[0]
        pad.addstr(n, 0, strs)
        span.append(len(strs) - 1)

    while key_toc != TOC and key_toc not in QUIT:
        if key_toc in SCROLL_UP and index > 0:
            index -= 1
        elif key_toc in SCROLL_DOWN and index + 1 < totlines:
            index += 1
        elif key_toc in FOLLOW:
            if index == oldindex:
                break
            return index
        elif key_toc in PAGE_UP:
            index = pgup(index, padhi)
        elif key_toc in PAGE_DOWN:
            if index >= totlines - padhi:
                index = totlines - 1
            else:
                index = pgdn(index, totlines, padhi)
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
            pre = "> " if index == n else "  "
            pad.chgat(n, 2, span[n], att)
            pad.addstr(n, 0, pre)

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
        mdata += textwrap.fill(i[0] + " : " + data, wi - 6).splitlines()
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

def reader(stdscr, ebook, index, width, y=0):
    k = 0 if SEARCHPATTERN is None else ord("/")
    rows, cols = stdscr.getmaxyx()
    x = (cols - width) // 2
    stdscr.clear()
    stdscr.refresh()

    chpath = ebook.get_contents()[index][1]

    content = ebook.file.open(chpath).read()

    # parser.body_width, imgs = width, []
    imgs, src_lines = [], []
    parser.body_width = False
    parser.single_line_break = True
    src = parser.handle(content.decode("utf-8"))
    # src_lines = src.splitlines() + [""]

    for i in src.splitlines():
        j = i
        if re.search("!\[.*?\]\(.*\)", i) != None:
            imgsrc = re.search("!\[.*?\]\(.*\)", i).group()
            imgsrc = re.sub("!\[.*?\]\(", "", imgsrc)
            imgsrc = re.sub("\)$", "", imgsrc)
            imgs.append(unquote(imgsrc))
            j = re.sub("!\[.*?\]\(.*\)", "[IMG:{}]".format(len(imgs)-1), i)
        src_lines += textwrap.fill(j.strip(), width).splitlines() + [""]

    pad = curses.newpad(len(src_lines), width + 2) # + 2 unnecessary
    pad.keypad(True)
    for i in range(len(src_lines)):
        if re.search("\[IMG:[0-9]+\]", src_lines[i]) != None:
            pad.addstr(i, width//2 - len(src_lines[i])//2 - RIGHTPADDING, src_lines[i], curses.A_REVERSE)
        else:
            pad.addstr(i, 0, src_lines[i])
    if index == 0:
        suff = "     End --> "
    elif index == len(ebook.get_contents()) - 1:
        suff = " <-- End     "
    else:
        suff = " <-- End --> "
    pad.addstr(i, width//2 - 7 - RIGHTPADDING, suff, curses.A_REVERSE)
    pad.refresh(y,0, 0,x, rows-1,x+width)

    while True:
        if k in QUIT:
            for i in state:
                state[i]["lastread"] = str(0)
            state[ebook.path]["lastread"] = str(1)
            state[ebook.path]["index"] = str(index)
            state[ebook.path]["width"] = str(width)
            state[ebook.path]["pos"] = str(y)
            with open(statefile, "w") as f:
                json.dump(state, f, indent=4)
            sys.exit()
        elif k in SCROLL_UP:
            if y > 0:
                y -= 1
        elif k in PAGE_UP:
            y = pgup(y, rows, LINEPRSRV)
        elif k in SCROLL_DOWN:
            if y < len(src_lines) - rows:
                y += 1
        elif k in PAGE_DOWN:
            if y + rows - LINEPRSRV <= len(src_lines) - rows:
                y += rows - LINEPRSRV
            elif len(src_lines) - y + LINEPRSRV > rows:
                y += rows - LINEPRSRV
                try:
                    stdscr.clear()
                    stdscr.refresh()
                    pad.refresh(y,0, 0,x, len(src_lines)-y,x+width)
                except curses.error:
                    pass
        elif k in CH_NEXT and index < len(ebook.get_contents()) - 1:
            return 1, width, 0
        elif k in CH_PREV and index > 0:
            return -1, width, 0
        elif k in CH_HOME:
            y = 0
        elif k in CH_END:
            y = pgend(len(src_lines), rows)
        elif k == TOC:
            fllwd = toc(stdscr, ebook, index, width)
            if fllwd is not None:
                if fllwd == curses.KEY_RESIZE:
                    k = fllwd
                    continue
                return fllwd - index, width, 0
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
            return 0, width, 0
        elif k == SHRINK and width >= 22:
            width -= 2
            return 0, width, 0
        elif k == ord("/"):
            fs = searching(stdscr, pad, src_lines, width, y, index, len(ebook.get_contents()))
            if fs == curses.KEY_RESIZE:
                k = fs
                continue
            elif SEARCHPATTERN is not None:
                return fs, width, 0
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
            # stated in pypi windows-curses page:
            # to call resize_term right after KEY_RESIZE
            if sys.platform == "win32":
                curses.resize_term(rows, cols)
                rows, cols = stdscr.getmaxyx()
            else:
                rows, cols = stdscr.getmaxyx()
                curses.resize_term(rows, cols)
            if cols <= width:
                width = cols - 2
            return 0, width, 0

        try:
            stdscr.clear()
            stdscr.refresh()
            pad.refresh(y,0, 0,x, rows-1,x+width)
        except curses.error:
            pass
        k = pad.getch()

def main(stdscr, file):
    curses.use_default_colors()
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
        idx = 0
        y = 0
        width = 80

    if cols <= width:
        width = cols - 2
        y = 0

    while True:
        incr, width, y = reader(stdscr, epub, idx, width, y)
        idx += incr

if __name__ == "__main__":
    args = []
    if sys.argv[1:] != []:
        args += sys.argv[1:]

    if len({"-h", "--help"} & set(args)) != 0:
        hlp = __doc__.rstrip()
        if "-h" in args:
            hlp = re.search("(\n|.)*(?=\n\nKey)", hlp).group()
        print(hlp)
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
        if val != 0 and len({"-r"} & set(args)) == 0:
            file = cand
        else:
            print("\nReading history:")
            for i in state.keys():
                print("- " + "(Last Read) " + i if state[i]["lastread"] == "1" else "- " + i)
            if len({"-r"} & set(args)) != 0:
                sys.exit()
            else:
                print()
                sys.exit("ERROR: Found no matching history.")

    if dump:
        epub = Epub(file)
        for i in epub.get_contents():
            parser.body_width = False
            parser.single_line_break = True
            imgs = []
            content = epub.file.open(i[1]).read()
            src = parser.handle(content.decode("utf-8"))
            for j in src.splitlines():
                sys.stdout.buffer.write((j+"\n\n").encode("utf-8"))
        sys.exit()

    else:
        curses.wrapper(main, file)
