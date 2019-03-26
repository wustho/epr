# `$ epr.py`

![Screenshot](https://raw.githubusercontent.com/wustho/epr/master/screenshot.png)

CLI Epub reader written in Python 3.7 with features:

- Remembers last read file (just run `epr.py` without any argument)
- Remembers last reading state for each file (per file saved state written to `$HOME/.epr`)
- Adjustable text area width
- Supports EPUB3 (tested on some, still no media supports though)
- Secondary vim-like bindings
- Supports image

Inspired by: https://github.com/aerkalov/ebooklib & https://github.com/rupa/epub

## Opening an Image
Just hit `o` when `[IMG:n]` (_n_ is any number) comes up on a page. If there's only one of those, it will automatically open the image using viewer, but if there are more than one, cursor will appear to help you choose which image then press `RET` to open it (`q` to cancel).

After you close the viewer and go back to reading, you might notice that `epr.py` lagging one keypress (I don't know how to explain, just feel it yourself), it happens to make sure that the image doesn't get deleted before you finish viewing it.

## Limitations

- [x] ~~Saving state doesn't work with a file that has `[]` in its name, e.g. `[EPUB]some_title.epub`. As workaround, just rename and remove `[]` from its name.~~
- [x] ~~Doesn't support images~~
- [x] ~~Doesn't support epub3~~
- Might not work well on heavily formatted epub, those with tables or code blocks, since initially written to read fictions.
- Minimum width: 22 cols
- Resizing terminal will reset to beginning of current chapter
- Saved state (reading position & width, but not reading chapter) will reset 
  if current terminal size is incompatible with latest reading state

## Dependencies

- ~~`html2text`~~
- `curses`

Started from `v1.2.0`, `epr.py` no longer requires `html2text` library. But if you have trouble with it or if you prefer reading in markdown, you probably need to go use older version provided in release page.

## Usage

To read an EPUBFILE:


```shell
$ epr.py EPUBFILE
```

To read last read epub:

```shell
$ epr.py
```

Key bindings:
```
    Help            : ?
    Quit            : q
    Scroll down     : ARROW DOWN    j
    Scroll up       : ARROW UP      k
    Page down       : PGDN          J   SPC
    Page up         : PGUP          K
    Next chapter    : ARROW RIGHT   l
    Prev chapter    : ARROW LEFT    h
    Beginning of ch : HOME          g
    End of ch       : END           G
    Open image      : o
    Shrink          : -
    Enlarge         : =
    TOC             : t
    Metadata        : m
```
