#!/usr/bin/env python3
"""
Usages:
    epr             read last epub
    epr FILE        read FILE
    epr -r          show reading history
    epr STRINGS     read STRINGS (best match) from history

Key binding:
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

locale.setlocale(locale.LC_ALL, "")

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

class HTMLtoLines(HTMLParser):
    global para, inde, bull, hide
    para = {"p", "div"}
    inde = {"q", "dt", "dd", "blockquote", "pre"}
    bull = {"li"}
    hide = {"script", "style", "head"}

    def __init__(self):
        HTMLParser.__init__(self)
        self.text = [""]
        self.imgs = []
        self.inde = False
        self.bull = False
        self.hide = False

    def handle_starttag(self, tag, attrs):
        if re.match("h[1-6]", tag) is not None:
            self.text[-1] += "[EPR:HEAD]"
        elif tag in para:
            if self.inde:
                self.text[-1] += "[EPR:INDE]"
            elif self.bull:
                self.text[-1] += "[EPR:BULL]"
        elif tag in inde:
            self.text[-1] += "[EPR:INDE]"
            self.inde = True
        elif tag in bull:
            self.text[-1] += "[EPR:BULL]"
            self.bull = True
        elif tag in hide:
            self.hide = True

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.text += [""]
            if self.inde:
                self.text[-1] += "[EPR:INDE]"
            elif self.bull:
                self.text[-1] += "[EPR:BULL]"
        elif tag == "img":
            for i in attrs:
                if i[0] == "src":
                    self.text.append("[IMG:{}]".format(len(self.imgs)))
                    self.imgs.append(unquote(i[1]))
                    self.text.append("")
        elif tag == "image":
            for i in attrs:
                if i[0] == "xlink:href":
                    self.text.append("[IMG:{}]".format(len(self.imgs)))
                    self.imgs.append(unquote(i[1]))
                    self.text.append("")

    def handle_endtag(self, tag):
        if re.match("h[1-6]", tag) is not None:
            self.text.append("")
            self.text.append("")
        elif tag in para:
            self.text.append("")
        elif tag in hide:
            self.hide = False
        elif tag in inde:
            if self.text[-1] != "":
                self.text.append("")
            self.inde = False
        elif tag in bull:
            if self.text[-1] != "":
                self.text.append("")
            self.bull = False

    def handle_data(self, raw):
        if raw and not self.hide:
            if self.text[-1] == "" or re.match(r"\[EPR:(INDE|BULL)\]", self.text[-1]) is not None:
                tmp = raw.lstrip()
            else:
                tmp = raw
            line = unescape(re.sub(r"\s+", " ", tmp))
            self.text[-1] += line

    def get_lines(self, width):
        text = []
        for i in self.text:
            if re.match(r"\[EPR:HEAD\]", i) is not None:
                tmp = i.replace("[EPR:HEAD]", "")
                text += [tmp.rjust(width//2 + len(tmp)//2 - RIGHTPADDING)] + [""]
            elif re.match(r"\[EPR:INDE\]", i) is not None:
                tmp = i.replace("[EPR:INDE]", "")
                text += ["   "+j for j in textwrap.fill(tmp, width - 3).splitlines()] + [""]
            elif re.match(r"\[EPR:BULL\]", i) is not None:
                tmp = i.replace("[EPR:BULL]", "")
                tmp = textwrap.fill(tmp, width - 3).splitlines()
                text += [" - "+j if j == tmp[0] else "   "+j for j in tmp] + [""]
            else:
                text += textwrap.fill(i, width).splitlines() + [""]
        return text, self.imgs

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
        elif key_toc in SCROLL_DOWN and index + 1 < len(src):
            index += 1
            top = pad(src, index, top)
        elif key_toc in FOLLOW:
            if index == oldindex:
                break
            return index
        elif key_toc == curses.KEY_RESIZE:
            return key_toc
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
        elif key_meta in SCROLL_DOWN and y < len(src_lines) - hi + 4:
            y += 1
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
        if key_help in SCROLL_UP and y > 0:
            y -= 1
        elif key_help in SCROLL_DOWN and y < len(src_lines) - hi + 4:
            y += 1
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

def reader(stdscr, ebook, index, width, y=0):
    k = 0
    rows, cols = stdscr.getmaxyx()
    x = (cols - width) // 2
    stdscr.clear()
    stdscr.refresh()

    chpath = ebook.get_contents()[index][1]

    content = ebook.file.open(chpath).read()
    content = content.decode("utf-8")

    parser = HTMLtoLines()
    try:
        parser.feed(content)
        parser.close()
    except:
        pass

    src_lines, imgs = parser.get_lines(width)

    pad = curses.newpad(len(src_lines), width + 2) # + 2 unnecessary
    pad.keypad(True)
    for i in range(len(src_lines)):
        if re.search("\[IMG:[0-9]+\]", src_lines[i]):
            pad.addstr(i, width//2 - len(src_lines[i])//2 - RIGHTPADDING, src_lines[i], curses.A_REVERSE)
        else:
            pad.addstr(i, 0, src_lines[i])
    pad.addstr(i, width//2 - 10 - RIGHTPADDING, "-- End of Chapter --", curses.A_REVERSE)
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
            if y >= rows - LINEPRSRV:
                y -= rows - LINEPRSRV
            else:
                y = 0
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
            # else:
            #     y = len(src_lines) - rows
            #     if y < 0:
            #         y = 0
        elif k in CH_NEXT and index < len(ebook.get_contents()) - 1:
            return 1, width
        elif k in CH_PREV and index > 0:
            return -1, width
        elif k in CH_HOME:
            y = 0
        elif k in CH_END:
            y = len(src_lines) - rows
            if y < 0:
                y = 0
        elif k == TOC:
            fllwd = toc(stdscr, ebook, index, width)
            if fllwd is not None:
                if fllwd == curses.KEY_RESIZE:
                    k = fllwd
                    continue
                return fllwd - index, width
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
            return 0, width
        elif k == SHRINK and width >= 22:
            width -= 2
            return 0, width
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
            return 0, width

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
        incr, width = reader(stdscr, epub, idx, width, y)
        idx += incr
        y = 0

if __name__ == "__main__":
    if len(sys.argv) == 1:
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
        else:
            curses.wrapper(main, file)
    else:
        if len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
            curses.wrapper(main, sys.argv[1])
        elif len({"-h", "--help"}.intersection(set(sys.argv[1:]))) != 0:
            print(__doc__)
        elif len({"-r"}.intersection(set(sys.argv[1:]))) != 0:
            print("\nReading history:")
            for i in state.keys():
                print("- " + "(Last Read) " + i if state[i]["lastread"] == "1" else "- " + i)
            print()
        else:
            val = cand = 0
            for i in state.keys():
                match_val = sum([j.size for j in SM(None, i.lower(), " ".join(sys.argv[1:]).lower()).get_matching_blocks()])
                if match_val >= val:
                    val = match_val
                    cand = i
            if val != 0:
                curses.wrapper(main, cand)
            else:
                print("\nReading history:")
                for i in state.keys():
                    print("- " + "(Last Read) " + i if state[i]["lastread"] == "1" else "- " + i)
                print()
                sys.exit("ERROR: Found no matching history.")
