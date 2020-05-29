#!/usr/bin/env python
# coding=utf-8

import pytest

from sacred.utils import (
    PATHCHANGE,
    convert_to_nested_dict,
    get_by_dotted_path,
    is_prefix,
    iter_prefixes,
    iterate_flattened,
    iterate_flattened_separately,
    join_paths,
    recursive_update,
    set_by_dotted_path,
    get_inheritors,
    convert_camel_case_to_snake_case,
    apply_backspaces_and_linefeeds,
    module_exists,
    module_is_in_cache,
    get_package_version,
    parse_version,
    rel_path,
)


def test_recursive_update():
    d = {"a": {"b": 1}}
    res = recursive_update(d, {"c": 2, "a": {"d": 3}})
    assert d is res
    assert res == {"a": {"b": 1, "d": 3}, "c": 2}


def test_iterate_flattened_separately():
    d = {
        "a1": 1,
        "b2": {"bar": "foo", "foo": "bar"},
        "c1": "f",
        "d1": [1, 2, 3],
        "e2": {},
    }
    res = list(iterate_flattened_separately(d, ["foo", "bar"]))
    assert res == [
        ("a1", 1),
        ("c1", "f"),
        ("d1", [1, 2, 3]),
        ("e2", {}),
        ("b2", PATHCHANGE),
        ("b2.foo", "bar"),
        ("b2.bar", "foo"),
    ]


def test_iterate_flattened():
    d = {"a": {"aa": 1, "ab": {"aba": 8}}, "b": 3}
    assert list(iterate_flattened(d)) == [("a.aa", 1), ("a.ab.aba", 8), ("b", 3)]


def test_set_by_dotted_path():
    d = {"foo": {"bar": 7}}
    set_by_dotted_path(d, "foo.bar", 10)
    assert d == {"foo": {"bar": 10}}


def test_set_by_dotted_path_creates_missing_dicts():
    d = {"foo": {"bar": 7}}
    set_by_dotted_path(d, "foo.d.baz", 3)
    assert d == {"foo": {"bar": 7, "d": {"baz": 3}}}


def test_get_by_dotted_path():
    assert get_by_dotted_path({"a": 12}, "a") == 12
    assert get_by_dotted_path({"a": 12}, "") == {"a": 12}
    assert get_by_dotted_path({"foo": {"a": 12}}, "foo.a") == 12
    assert get_by_dotted_path({"foo": {"a": 12}}, "foo.b") is None


def test_iter_prefixes():
    assert list(iter_prefixes("foo.bar.baz")) == ["foo", "foo.bar", "foo.bar.baz"]


def test_join_paths():
    assert join_paths() == ""
    assert join_paths("foo") == "foo"
    assert join_paths("foo", "bar") == "foo.bar"
    assert join_paths("a", "b", "c", "d") == "a.b.c.d"
    assert join_paths("", "b", "", "d") == "b.d"
    assert join_paths("a.b", "c.d.e") == "a.b.c.d.e"
    assert join_paths("a.b.", "c.d.e") == "a.b.c.d.e"


def test_is_prefix():
    assert is_prefix("", "foo")
    assert is_prefix("foo", "foo.bar")
    assert is_prefix("foo.bar", "foo.bar.baz")

    assert not is_prefix("a", "foo.bar")
    assert not is_prefix("a.bar", "foo.bar")
    assert not is_prefix("foo.b", "foo.bar")
    assert not is_prefix("foo.bar", "foo.bar")


def test_convert_to_nested_dict():
    dotted_dict = {"foo.bar": 8, "foo.baz": 7}
    assert convert_to_nested_dict(dotted_dict) == {"foo": {"bar": 8, "baz": 7}}


def test_convert_to_nested_dict_nested():
    dotted_dict = {"a.b": {"foo.bar": 8}, "a.b.foo.baz": 7}
    assert convert_to_nested_dict(dotted_dict) == {
        "a": {"b": {"foo": {"bar": 8, "baz": 7}}}
    }


def test_get_inheritors():
    class A:
        pass

    class B(A):
        pass

    class C(B):
        pass

    class D(A):
        pass

    class E:
        pass

    assert get_inheritors(A) == {B, C, D}


@pytest.mark.parametrize(
    "name,expected",
    [
        ("CamelCase", "camel_case"),
        ("snake_case", "snake_case"),
        ("CamelCamelCase", "camel_camel_case"),
        ("Camel2Camel2Case", "camel2_camel2_case"),
        ("getHTTPResponseCode", "get_http_response_code"),
        ("get2HTTPResponseCode", "get2_http_response_code"),
        ("HTTPResponseCode", "http_response_code"),
        ("HTTPResponseCodeXYZ", "http_response_code_xyz"),
    ],
)
def test_convert_camel_case_to_snake_case(name, expected):
    assert convert_camel_case_to_snake_case(name) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", ""),
        ("\b", ""),
        ("\r", "\r"),
        ("\r\n", "\n"),
        ("ab\bc", "ac"),
        ("\ba", "a"),
        ("ab\nc\b\bd", "ab\nd"),
        ("abc\rdef", "def"),
        ("abc\r", "abc\r"),
        ("abc\rd", "dbc"),
        ("abc\r\nd", "abc\nd"),
        ("abc\ndef\rg", "abc\ngef"),
        ("abc\ndef\r\rg", "abc\ngef"),
        ("abcd\refg\r", "efgd\r"),
        ("abcd\refg\r\n", "efgd\n"),
    ],
)
def test_apply_backspaces_and_linefeeds(text, expected):
    assert apply_backspaces_and_linefeeds(text) == expected


def test_module_exists_base_level_modules():
    assert module_exists("pytest")
    assert not module_exists("clearly_non_existing_module_name")


def test_module_exists_does_not_import_module():
    assert module_exists("tests.donotimport")


def test_module_is_in_cache():
    assert module_is_in_cache("pytest")
    assert module_is_in_cache("pkgutil")
    assert not module_is_in_cache("does_not_even_exist")


def test_get_package_version():
    package_version = get_package_version("pytest")
    assert str(package_version) == "4.3.0"


def test_parse_version():
    parsed_version = parse_version("4.3.0")
    assert str(parsed_version) == "4.3.0"


def test_get_package_version_comparison():
    package_version = get_package_version("pytest")
    current_version = parse_version("4.3.0")
    old_version = parse_version("4.2.1")
    new_version = parse_version("4.4.1")
    assert package_version == current_version
    assert not package_version < current_version
    assert not package_version > current_version
    assert package_version <= new_version
    assert package_version >= old_version


def test_rel_path():
    assert rel_path("", "foo.bar.baz") == "foo.bar.baz"
    assert rel_path("foo", "foo.bar.baz") == "bar.baz"
    assert rel_path("foo.bar", "foo.bar.baz") == "baz"
    assert rel_path("foo.bar.baz", "foo.bar.baz") == ""
    assert rel_path("", "") == ""
