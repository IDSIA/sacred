#!/usr/bin/env python
# coding=utf-8
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

classifiers = """
Development Status :: 4 - Beta
Intended Audience :: Science/Research
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
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
    ext_modules = []
    # Manually extract the __about__
    about = dict()
    exec(open("sacred/__about__.py").read(), about)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='sacred',
    version=about['__version__'],

    author=about['__author__'],
    author_email=about['__author_email__'],

    url=about['__url__'],

    packages=['sacred', 'sacred.observers', 'sacred.config'],
    scripts=[],
    install_requires=[
        'docopt', 'six', 'wrapt'
    ],
    tests_require=['mock', 'mongomock', 'pytest'],
    cmdclass={'test': PyTest},

    classifiers=list(filter(None, classifiers.split('\n'))),
    description='Facilitates automated and reproducible experimental research',
    long_description=open('README.rst').read()
)
