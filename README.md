# `$ epr.py`

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

# License

MIT License

Copyright (c) 2019 Benawi Adha

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

