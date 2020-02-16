# `$ epr` [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![Screenshot](https://raw.githubusercontent.com/wustho/epr/master/screenshot.png)

Terminal/CLI Epub reader written in Python 3.6 with features:

- Remembers last read file (just run `epr` without any argument)
- Remembers last reading state for each file (per file saved state written to `$HOME/.config/epr/config` or `$HOME/.epr` respectively depending on availability)
- Adjustable text area width
- Adaptive to terminal resize
- Supports EPUB3 (no audio support)
- Secondary vim-like bindings
- Supports opening images
- Dark/Light colorscheme (depends on terminal color capability)

## Limitations

- Minimum width: 22 cols
- Supports regex search only
- Supports only horizontal left-to-right text
- Doesn't support hyperlinks
- Some known issues mentioned below
- Customizing keybindings & colorscheme done inside the source code itself (no separated config file)

## Dependencies

- `curses` (Linux) or `windows-curses` (Windows)

## Installation

Clone this repo, tweak `epr.py` as much as you see fit, rename it to `epr`, make it executable and put it somewhere in `PATH`.
Or simply (be careful if you already have package named `epr` installed):

```shell
$ pip3 install git+https://github.com/wustho/epr.git
```

Via chocolatey (maintained by [cybercatgurrl](https://github.com/cybercatgurrl/chocolatey-pkgs/tree/master/epr)):

```shell
$ choco install epr
```

From the AUR (maintained by [jneidel](https://aur.archlinux.org/packages/epr-git/)):

```shell
$ yay -S epr-git
```

## Quickly Read from History

Rather than invoking `epr /path/to/file` each time you are going to read, you might find it easier to do just `epr STRINGS.`

Example:

``` shell
$ epr dumas count mont
```

If `STRINGS` is not any file, `epr` will choose from reading history, best matched `path/to/file` with those `STRINGS.` So, the more `STRINGS` given the more accurate it will find.

Run `epr -r` to show list of all reading history.

## Opening an Image

Just hit `o` when `[IMG:n]` (_n_ is any number) comes up on a page. If there's only one of those, it will automatically open the image using viewer, but if there are more than one, cursor will appear to help you choose which image then press `RET` to open it and `q` to cancel.

## Colorscheme

This is just a simple colorscheme involving foreground dan background color only, no syntax highlighting.
You can cycle color between default terminal color, dark or light respectively by pressing `c`.
You can also switch color to default, dark or light by pressing `0c`, `1c` or `2c` respectively.

Customizing dark/light colorscheme needs to be done inside the source code by editing these lines:

```python
# colorscheme
# DARK/LIGHT = (fg, bg)
# -1 is default terminal fg/bg
DARK = (252, 235)
LIGHT = (239, 223)
```

To see available values assigned to colors, you can run this one-liner on bash:

```shell
$ i=0; for j in {1..16}; do for k in {1..16}; do printf "\e[1;48;05;${i}m %03d \e[0m" $i; i=$((i+1)); done; echo; done
```

## Vanilla or Markdown?

[UNMAINTAINED]

If you'd like to read epub in markdown format, which _requires_ additional dependency: `html2text`, checkout `markdown` branch of this repo or simply:

```shell
$ pip3 install git+https://github.com/wustho/epr.git@markdown
```

Useful when you read more nonfiction reference epub (like manual or documentation) than fiction one.

## Reading Progress Indicator

If you need reading progress indicator and you don't mind a little more startup time, checkout [epy](https://github.com/wustho/epy).
It's just my fork of this `epr`, but with one extra feature: **Reading Progress Percentage**.

## Usages

```
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
    Toggle width    : =
    Set width       : [count]=
    Shrink          : -
    Enlarge         : +
    ToC             : TAB       t
    Metadata        : m
    Switch colorsch : [default=0, dark=1, light=2]c
```

## Known Issues

1. Search function can't find occurences that span across multiple lines

   Only capable of finding pattern that span inside a single line, not sentence.
   So works more effectively for finding word or letter rather than long phrase or sentence.

   As workarounds, You can increase text area width to increase its reach or dump
  the content of epub using `-d` option, which will dump each paragraph into a single line separated by empty line (or lines depending on the epub), to be later piped into `grep`, `rg` etc. Pretty useful to find book quotes.

   Example:

   ```shell
   # to get 1 paragraph before and after a paragraph containing "Overdue"
   $ epr -d the_girl_next_door.epub | grep Overdue -C 2
   ```

2. <sup>Superscript</sup> and <sub>subscript</sub> displayed as `^{Superscript}` and `_{subscript}`.

3. Some TOC issues:

   - "-" chapters in TOC

     This happens because not every chapter file (inside some epubs) is given navigation points.
     Some epubs even won't let you navigate between chapter, thus you'll find all chapters named as
     "-" using `epr` for these kind of epubs.

   - Skipped chapters in TOC

     Example:

     ```
     Table of Contents
     -----------------

         1. Title Page
         2. Chapter I
         3. Chapter V
     ```

     This happens because Chapter II to Chapter IV is probably in the same file with Chapter I,
     but in different sections, e. g. `ch000.html#section1` and `ch000.html#section2.`

     But don't worry, you should not miss any part to read. This just won't let you navigate
     to some points using TOC.

   If you feel bothered by these 2 TOC issues, checkout branch `commontoc` or install via:

   ```shell
   $ pip3 install git+https://github.com/wustho/epr.git@commontoc
   ```

   which will give you TOC behavior like in many common readers.

   NOTE: I'm not merging `commontoc` to `master` since `master` already does most of its job efficiently and (supposedly, I'm not doing any test) faster. It just navigates between files inside epub rather than pre-defined sections like `commontoc` does.

## Inspirations

- https://github.com/aerkalov/ebooklib
- https://github.com/rupa/epub
