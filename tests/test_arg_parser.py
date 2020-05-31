#!/usr/bin/env python
# coding=utf-8


import pytest
import shlex
from docopt import docopt

from sacred.arg_parser import _convert_value, get_config_updates, format_usage
from sacred.experiment import gather_command_line_options


@pytest.mark.parametrize(
    "argv,expected",
    [
        ("", {}),
        ("run", {"COMMAND": "run"}),
        ("with 1 2", {"with": True, "UPDATE": ["1", "2"]}),
        ("evaluate", {"COMMAND": "evaluate"}),
        ("help", {"help": True}),
        ("help evaluate", {"help": True, "COMMAND": "evaluate"}),
        ("-h", {"--help": True}),
        ("--help", {"--help": True}),
        ("-m foo", {"--mongo_db": "foo"}),
        ("--mongo_db=bar", {"--mongo_db": "bar"}),
        ("-l 10", {"--loglevel": "10"}),
        ("--loglevel=30", {"--loglevel": "30"}),
        ("--force", {"--force": True}),
        (
            "run with a=17 b=1 -m localhost:22222",
            {
                "COMMAND": "run",
                "with": True,
                "UPDATE": ["a=17", "b=1"],
                "--mongo_db": "localhost:22222",
            },
        ),
        (
            "evaluate with a=18 b=2 -l30",
            {
                "COMMAND": "evaluate",
                "with": True,
                "UPDATE": ["a=18", "b=2"],
                "--loglevel": "30",
            },
        ),
    ],
)
def test_parse_individual_arguments(argv, expected):
    options = gather_command_line_options()
    usage = format_usage("test.py", "", {}, options)
    argv = shlex.split(argv)
    plain = docopt(usage, [], help=False)
    args = docopt(usage, argv, help=False)
    plain.update(expected)
    assert args == plain


@pytest.mark.parametrize(
    "update,expected",
    [
        (None, {}),
        (["a=5"], {"a": 5}),
        (["foo.bar=6"], {"foo": {"bar": 6}}),
        (["a=9", "b=0"], {"a": 9, "b": 0}),
        (["hello='world'"], {"hello": "world"}),
        (['hello="world"'], {"hello": "world"}),
        (["f=23.5"], {"f": 23.5}),
        (["n=None"], {"n": None}),
        (["t=True"], {"t": True}),
        (["f=False"], {"f": False}),
    ],
)
def test_get_config_updates(update, expected):
    assert get_config_updates(update) == (expected, [])


@pytest.mark.parametrize(
    "value,expected",
    [
        ("None", None),
        ("True", True),
        ("False", False),
        ("246", 246),
        ("1.0", 1.0),
        ("1.", 1.0),
        (".1", 0.1),
        ("1e3", 1e3),
        ("-.4e-12", -0.4e-12),
        ("-.4e-12", -0.4e-12),
        ("[1,2,3]", [1, 2, 3]),
        ("[1.,.1]", [1.0, 0.1]),
        ("[True, False]", [True, False]),
        ("[None, None]", [None, None]),
        ("[1.0,2.0,3.0]", [1.0, 2.0, 3.0]),
        ('{"a":1}', {"a": 1}),
        ('{"foo":1, "bar":2.0}', {"foo": 1, "bar": 2.0}),
        ('{"a":1., "b":.2}', {"a": 1.0, "b": 0.2}),
        ('{"a":True, "b":False}', {"a": True, "b": False}),
        ('{"a":None}', {"a": None}),
        (
            '{"a":[1, 2.0, True, None], "b":"foo"}',
            {"a": [1, 2.0, True, None], "b": "foo"},
        ),
        ("bob", "bob"),
        ('"hello world"', "hello world"),
        ("'hello world'", "hello world"),
    ],
)
def test_convert_value(value, expected):
    assert _convert_value(value) == expected
