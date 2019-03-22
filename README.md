# epr

![Screenshot](https://raw.githubusercontent.com/wustho/epr/master/screenshot.png)

CLI Epub reader written in Python 3.7 with features:

- remember last read file (just run `epr.py` without any argument)
- remember last reading state for each file (per file saved state written to `$HOME/.epr`)
- adjustable text area width

Inspired by: https://github.com/aerkalov/ebooklib & https://github.com/rupa/epub

## Limitations

- doesn't support images
- doesn't support epub3
- minimum width: 22 cols
- resizing terminal will reset to beginning of current chapter
- saved state (reading position & width, but not reading chapter) will reset 
  if current terminal size is incompatible with latest reading state

## Dependancies

- `html2text`
- `curses`

## Usages

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
    Help            : h, ?
    Quit            : q
    Scroll down     : ARROW DOWN
    Scroll up       : ARROW UP
    Page down       : PGUP
    Page up         : PGDN
    Next chapter    : ARROW RIGHT
    Prev chapter    : ARROW LEFT
    Beginning of ch : HOME
    End of ch       : END
    Shrink          : -
    Enlarge         : =
    TOC             : t
    Metadata        : m
```
