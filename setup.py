import sys
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="epr-reader",
    version="2.4.13",
    description="Terminal/CLI Epub Reader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wustho/epr",
    author="Benawi Adha",
    author_email="benawiadha@gmail.com",
    license="MIT",
    keywords=["EPUB", "EPUB3", "CLI", "Terminal", "Reader"],
    install_requires=["windows-curses;platform_system=='Windows'"],
    python_requires="~=3.3",
    py_modules=["epr"],
    entry_points={ "console_scripts": ["epr=epr:main"] },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
