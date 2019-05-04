import sys
from setuptools import setup
from epr import __version__

setup(
    name = "epr",
    version = __version__,
    description = "Terminal/CLI Epub Reader",
    url = "https://github.com/wustho/epr",
    author = "Benawi Adha",
    license = "MIT",
    keywords = ["EPUB", "EPUB3", "CLI", "Terminal", "Reader"],
    install_requires = ["windows-curses"] if sys.platform == "win32" else [],
    python_requires = "~=3.7",
    py_modules = ["epr"],
    entry_points = { "console_scripts": ["epr = epr:main"] }
)
