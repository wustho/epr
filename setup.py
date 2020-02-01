import sys
from setuptools import setup
from epr import __version__, __author__, __url__, __license__

setup(
    name = "epr",
    version = __version__,
    description = "Terminal/CLI Epub Reader",
    url = __url__,
    author = __author__,
    license = __license__,
    keywords = ["EPUB", "EPUB3", "CLI", "Terminal", "Reader"],
    install_requires = ["windows-curses"] if sys.platform == "win32" else [],
    python_requires = "~=3.6",
    py_modules = ["epr"],
    entry_points = { "console_scripts": ["epr = epr:main"] }
)
