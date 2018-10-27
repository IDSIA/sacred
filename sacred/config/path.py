#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import ast
import re
from copy import copy, deepcopy
from collections import Sequence
from functools import total_ordering


@total_ordering
class Path(Sequence):
    """
    Immutable path object
    """
    __slots__ = ('parts',)

    PYTHON_IDENTIFIER = re.compile(r"^[a-zA-Z_][_a-zA-Z0-9]*$")

    PART = re.compile(""" # part can be:
        ([a-zA-Z_][_a-zA-Z0-9]*)|       # a valid python identifier 
        (?:\[([^\]]+)\])| # enclosed in brackets
        (?:\"([^"]+)\")|  # enclosed in ""
        (?:\'([^']+)\')   # enclosed in ''
        """, flags=re.VERBOSE)

    str_part = """(([a-zA-Z_][_a-zA-Z0-9]*)|(?:\"([^"]+)\")|(?:\'([^']+)\'))"""
    bracket_part = "(?:\[([^\]]+)\])"

    PATH = re.compile(
        "^({str_part}|{bracket_part})(\.{str_part}|{bracket_part})*$".format(
            str_part=str_part, bracket_part=bracket_part))

    def __init__(self, *parts):
        self.parts = parts
        super().__init__()

    def __len__(self):
        return len(self.parts)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return Path(*self.parts[index])
        else:
            return self.parts[index]

    def __add__(self, other):
        if isinstance(other, Path):
            return Path(*(self.parts + other.parts))
        elif isinstance(other, str):
            other = Path.from_str(other)
            return Path(*(self.parts + other.parts))
        else:
            raise TypeError("Can't convert '{}' object to Path implicitly."
                            .format(type(other)))

    def __radd__(self, other):
        if isinstance(other, Path):
            return Path(*(other.parts + self.parts))
        elif isinstance(other, str):
            other = Path.from_str(other)
            return Path(*(other.parts + self.parts))
        else:
            raise TypeError("Can't convert '{}' object to Path implicitly."
                            .format(type(other)))

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        if isinstance(other, Path):
            return self.parts == other.parts
        elif isinstance(other, str):
            other = Path.from_str(other)
            return self.parts == other.parts
        else:
            return False

    def __gt__(self, other):
        if isinstance(other, Path):
            return self.parts > other.parts
        elif isinstance(other, str):
            other = Path.from_str(other)
            return self.parts > other.parts
        else:
            raise TypeError("unorderable types: Path < {}".format(type(other)))

    def __repr__(self):
        return 'p"' + self.__str__() + '"'

    def __str__(self):
        r = "".join([self.format_part(p) for p in self.parts])
        r = r[1:] if r and r[0] == '.' else r
        return r

    def __enter__(self):
        """Allow entering a path for convenience and better error reporting.
        Example:
            with path as (first, rest):
              cfg = cfg[first]
        """
        return self.pop()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: integrate with SacredErrors
        if exc_type in (AttributeError, IndexError, KeyError, TypeError):
            if not exc_val.args or not isinstance(exc_val.args[-1], Path):
                exc_val.args += (self[:1],)
            else:
                exc_val.args = exc_val.args[:-1] + (self[:1] + exc_val.args[-1],)

    def __getstate__(self):
        return str(self)

    def __copy__(self):
        return Path(*copy(self.parts))

    def __deepcopy__(self, cache):
        return Path(*deepcopy(self.parts, cache))

    def pop(self):
        return self[0], self[1:]

    @classmethod
    def parse_path(cls, path):
        def parse_value(value):
            """Parse as python literal if possible, fallback to string."""
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                # use as string if nothing else worked
                return value

        def parse_part_match(pm):
            if pm[1]:  # this group corresponds to the [...] case
                return parse_value(pm[1])
            else:  # these groups correspond to the ..., "...", and '...' cases
                return pm[0] or pm[2] or pm[3]

        return [parse_part_match(pm) for pm in cls.PART.findall(path)]

    @classmethod
    def from_str(cls, s):
        if cls.PATH.match(s):
            return cls(*(cls.parse_path(s)))
        else:
            return cls(s)

    @classmethod
    def from_any(cls, o):
        if isinstance(o, Path):
            return o
        elif isinstance(o, str):
            return cls.from_str(o)
        elif isinstance(o, (tuple, list)):
            return cls(*o)
        else:
            return cls(o)

    @classmethod
    def format_part(cls, p):
        if isinstance(p, str):
            if cls.PYTHON_IDENTIFIER.match(p):
                return "." + p
            else:
                return ".'" + p + "'"
        else:
            return "[" + str(p) + "]"
