import sys
from setuptools import setup
from epr import __version__, __author__, __email__, __url__, __license__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="epr-reader",
    version=__version__,
    description="Terminal/CLI Epub Reader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=__url__,
    author=__author__,
    author_email=__email__,
    license=__license__,
    keywords=["EPUB", "EPUB3", "CLI", "Terminal", "Reader"],
    install_requires=["windows-curses"] if sys.platform == "win32" else [],
    python_requires="~=3.6",
    py_modules=["epr"],
    entry_points={ "console_scripts": ["epr=epr:main"] },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
