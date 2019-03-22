# epr

[Screenshot]()

CLI Epub reader written in Python 3.7 with features:

- remember last read file (just run `epr.py` without any argument)
- remember last reading state for each file (per file saved state written to `$HOME/.epr`)
- adjustable text area width

Inspired by: rupa/epub TODO

## LIMITATIONS

- doesn't support images
- doesn't support epub3
- minimum width: 22 cols
- resizing terminal will reset to beginning of current chapter
- saved state (reading position & width, but not reading chapter) will reset 
  if current terminal size is incompatible with latest reading state

## DEPENDANCIES

- `html2text`
- `curses`

## USAGE

```
Usage:
    to read an EPUBFILE:
        epr.py EPUBFILE
        python3 epr.py EPUBFILE

    to read last read epub:
        epr.py


Key binding:
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
