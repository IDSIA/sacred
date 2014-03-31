#!/usr/bin/python
# coding=utf-8

from distutils.core import setup
import sperment

classifiers = """
Development Status :: 3 - Alpha
Intended Audience :: Science/Research
License :: OSI Approved :: GNU General Public License v3 (GPLv3)
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Topic :: Utilities
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Artificial Intelligence
Topic :: Software Development :: Libraries
Topic :: Software Development :: Quality Assurance
"""


setup(
    name='sperment',
    version=sperment.__version__,
    author='Klaus Greff',
    author_email='qwlouse@gmail.com',
    packages=['sperment', 'sperment.test'],
    classifiers=filter(None, classifiers.split('\n')),
    scripts=[],
    license='LICENSE',
    description='Facilitates reproducible research.',
    long_description=open('README.md').read(),
    install_requires=[
        "bunch >= 1.0"
    ],
)
