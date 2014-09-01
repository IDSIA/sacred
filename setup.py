#!/usr/bin/env python
# coding=utf-8

from setuptools import setup

classifiers = """
Development Status :: 3 - Alpha
Intended Audience :: Science/Research
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.2
Programming Language :: Python :: 3.4
Programming Language :: Python :: Implementation :: PyPy
Topic :: Utilities
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Artificial Intelligence
Topic :: Software Development :: Libraries
Topic :: Software Development :: Quality Assurance
"""

try:
    from sacred import __about__
    about = __about__.__dict__
except ImportError:
    # installing - dependencies are not there yet
    ext_modules = []
    # Manually extract the __about__
    about = dict()
    execfile("sacred/__about__.py", about)


setup(
    name='sacred',
    version=about['__version__'],

    author=about['__author__'],
    author_email=about['__author_email__'],

    packages=['sacred'],
    test_suite="tests",
    scripts=[],
    install_requires=[
        'pytest', 'docopt', 'wrapt'
    ],

    classifiers=filter(None, classifiers.split('\n')),
    description='Facilitates reproducible and automated research.',
    long_description=open('README.md').read(),
    license='LICENSE',
)
