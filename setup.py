#!/usr/bin/env python
# coding=utf-8

import codecs

from setuptools import setup

classifiers = """
Development Status :: 5 - Production/Stable
Intended Audience :: Science/Research
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Topic :: Utilities
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Artificial Intelligence
Topic :: Software Development :: Libraries :: Python Modules
License :: OSI Approved :: MIT License
"""

try:
    from sacred import __about__

    about = __about__.__dict__
except ImportError:
    # installing - dependencies are not there yet
    # Manually extract the __about__
    about = dict()
    exec(open("sacred/__about__.py").read(), about)


setup(
    name="sacred",
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    packages=["sacred", "sacred.observers", "sacred.config", "sacred.stflow"],
    scripts=[],
    install_requires=[
        "docopt>=0.3, <1.0",
        "jsonpickle>=0.7.2, <1.0",
        "munch>=2.0.2, <3.0",
        "wrapt>=1.0, <2.0",
        "py-cpuinfo>=4.0",
        "colorama>=0.4",
        "packaging>=18.0",
        "boto3>=1.9.0",
    ],
    tests_require=["mock>=0.8, <3.0", "pytest==4.3.0"],
    classifiers=list(filter(None, classifiers.split("\n"))),
    description="Facilitates automated and reproducible experimental research",
    long_description=codecs.open("README.rst", encoding="utf_8").read(),
)
