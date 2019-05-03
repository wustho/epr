import os, re, sys, shutil
from setuptools import setup

os.makedirs("epr", exist_ok=True)
with open(os.path.join("epr", "__init__.py"), "w+") as initfile:
    initfile.write("")
shutil.copy("epr.py", os.path.join("epr", "__main__.py"))

with open("README.md", "r") as f:
    longdesc = f.read()

with open("epr.py", "r") as f:
    for i in f:
        v = re.search("(?<=Version :).*", i)
        if v is not None:
            vers = v.group().lstrip().rstrip()
            break

setup(
    name = "epr",
    version = vers,
    description = "Terminal/CLI Epub reader",
    long_description = longdesc,
    long_description_content_type = "text/markdown",
    url = "https://github.com/wustho/epr",
    author = "Benawi Adha",
    license = "MIT",
    keywords = ["EPUB", "EPUB3", "CLI", "Terminal", "Reader"],
    packages = ["epr"],
    install_requires = ["windows-curses"] if sys.platform == "win32" else [],
    python_requires = "~=3.7",
    entry_points = { "console_scripts": ["epr = epr.__main__:main"] }
)

shutil.rmtree("epr")
