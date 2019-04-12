# `$ epr.py`

![Screenshot](https://raw.githubusercontent.com/wustho/epr/master/screenshot.png)

CLI Epub reader written in Python 3.7 with features:

- Remembers last read file (just run `epr.py` without any argument)
- Remembers last reading state for each file (per file saved state written to `$HOME/.config/epr/config` or `$HOME/.epr` respectively depending on availability)
- Adjustable text area width
- Supports EPUB3 (no audio support)
- Secondary vim-like bindings
- Supports image

Inspired by: https://github.com/aerkalov/ebooklib & https://github.com/rupa/epub

## Limitations

- Minimum width: 22 cols
- Resizing terminal & text area width will reset to beginning of current chapter
- Saved state (reading position & width, but not reading chapter) will reset
  if current terminal size is incompatible with latest reading state

## Quickly Read from History

Rather than invoking `epr.py /path/to/file` each time you are going to read, you might find it easier to do just `epr.py STRINGS.` If `STRINGS` is not any file, `epr.py` will choose from reading history, best matched `path/to/file` with those `STRINGS.` So, the more `STRINGS` given the more accurate it will find.

Run `epr.py -r` to show list of all reading history.

## Opening an Image

Just hit `o` when `[IMG:n]` (_n_ is any number) comes up on a page. If there's only one of those, it will automatically open the image using viewer, but if there are more than one, cursor will appear to help you choose which image then press `RET` to open it (`q` to cancel).

## Vanilla or Markdown?

If you'd like to read epub in markdown format, checkout `v2.0.1-md` (which _requires_ module `html2text`) from release page.
e.g. when you read nonfiction reference epub (like manual or documentation) rather than fiction one.

## Dependencies

- `curses`

## Usages

Usages:

```
epr             read last epub
epr FILE        read FILE
epr -r          show reading history
epr STRINGS     read STRINGS (best match) from history
```

Key binding:

```
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
```
