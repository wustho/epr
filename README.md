# `$ epr.py`

![Screenshot](https://raw.githubusercontent.com/wustho/epr/master/screenshot.png)

CLI Epub reader written in Python 3.7 with features:

- remember last read file (just run `epr.py` without any argument)
- remember last reading state for each file (per file saved state written to `$HOME/.epr`)
- adjustable text area width
- support EPUB3 (tested on some, still no media supports though)
- added secondary vim-like key bindings
- image support **[TEST]**

  Just hit `o` when `[IMG:n]` (_n_ is any number) comes up on a page. If there's only one of those, it will automatically open the image using viewer, but if there are more than one, cursor will appear to help you choose which image then press `RET` to open it (`q` to cancel).

  After you close the viewer and go back to reading, you might notice that `epr.py` lagging one keypress (I don't know how to explain, just feel it yourself), it happens to make sure that the image doesn't get deleted before you finish viewing it.

  As for supported viewers, I need your helps, because it happens that I broke my linux sometimes ago so I can't test it on my own (The main reason I wrote `epr.py` is to have decent looking & minimalist epub reader which can run on whatever platform as long as it has python). And I only tested it on windows. But I preprogrammed some viewer: `feh`, `gnome-open`, `xdg-open`, and `kde-open`. So if you try this on PC that has `feh` or running gnome, xface, or kde without `feh`, please tell me the result by opening issue or email me, or probably you have other viewers to suggest.

  And for those asking for displaying image in terminal like `neofetch`, sorry but I tried to make this as minimalist as possible. By harnessing whatever already in PC running this, I don't need to install additional stuff. So I can focus on reading Ring by Koji Suzuki, It's good really, on par with the movie.

Inspired by: https://github.com/aerkalov/ebooklib & https://github.com/rupa/epub

## Limitations

- [x] ~~saving state doesn't work with a file that has `[]` in its name, e.g. `[EPUB]some_title.epub`. As workaround, just rename and remove `[]` from its name.~~
- [TEST] ~~doesn't~~ support images
- [x] ~~doesn't support epub3~~
- minimum width: 22 cols
- resizing terminal will reset to beginning of current chapter
- saved state (reading position & width, but not reading chapter) will reset 
  if current terminal size is incompatible with latest reading state

## Dependencies

- ~~`html2text`~~
- `curses`

Started from `v1.2.0`, `epr.py` no longer requires `html2text` library. But if you have trouble with it, you probably need to go use older version provided in release page.

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
