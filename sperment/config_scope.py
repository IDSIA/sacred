#!/usr/bin/python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
from bunch import Bunch
import json


class TransformToBunch(type):
    def __new__(mcs, name, bases, dct):
        if '__transform__' in dct and not dct['__transform__']:
            return super(TransformToBunch, mcs).__new__(mcs, name, bases, dct)
        else:
            b = Bunch()
            for k, v in dct.items():
                if k.startswith('__'):
                    continue
                try:
                    json.dumps(v)
                    b[k] = v
                except TypeError:
                    pass
            return b


class ConfigScope(object):
    """
    Any class inheriting from this class will act as a scope for defining
    configuration. The result of the class definition will not be class but a
    Bunch object (a kind of dict).
    """
    __metaclass__ = TransformToBunch
    __transform__ = False