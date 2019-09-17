#!/usr/bin/env python
# coding=utf-8


import pytest

pymongo = pytest.importorskip("pymongo")

from sacred.observers.mongo import parse_mongo_db_arg, DEFAULT_MONGO_PRIORITY


def test_parse_mongo_db_arg():
    assert parse_mongo_db_arg("foo") == {"db_name": "foo"}


def test_parse_mongo_db_arg_collection():
    kwargs = parse_mongo_db_arg("foo.bar")
    assert kwargs == {"db_name": "foo", "collection": "bar"}


def test_parse_mongo_db_arg_hostname():
    assert parse_mongo_db_arg("localhost:28017") == {"url": "localhost:28017"}

    assert parse_mongo_db_arg("www.mymongo.db:28017") == {"url": "www.mymongo.db:28017"}

    assert parse_mongo_db_arg("123.45.67.89:27017") == {"url": "123.45.67.89:27017"}


def test_parse_mongo_db_arg_hostname_dbname():
    assert parse_mongo_db_arg("localhost:28017:foo") == {
        "url": "localhost:28017",
        "db_name": "foo",
    }

    assert parse_mongo_db_arg("www.mymongo.db:28017:bar") == {
        "url": "www.mymongo.db:28017",
        "db_name": "bar",
    }

    assert parse_mongo_db_arg("123.45.67.89:27017:baz") == {
        "url": "123.45.67.89:27017",
        "db_name": "baz",
    }


def test_parse_mongo_db_arg_hostname_dbname_collection_name():
    assert parse_mongo_db_arg("localhost:28017:foo.bar") == {
        "url": "localhost:28017",
        "db_name": "foo",
        "collection": "bar",
    }

    assert parse_mongo_db_arg("www.mymongo.db:28017:bar.baz") == {
        "url": "www.mymongo.db:28017",
        "db_name": "bar",
        "collection": "baz",
    }

    assert parse_mongo_db_arg("123.45.67.89:27017:baz.foo") == {
        "url": "123.45.67.89:27017",
        "db_name": "baz",
        "collection": "foo",
    }


def test_parse_mongo_db_arg_priority():
    assert parse_mongo_db_arg("localhost:28017:foo.bar!17") == {
        "url": "localhost:28017",
        "db_name": "foo",
        "collection": "bar",
        "priority": 17,
    }

    assert parse_mongo_db_arg("www.mymongo.db:28017:bar.baz!2") == {
        "url": "www.mymongo.db:28017",
        "db_name": "bar",
        "collection": "baz",
        "priority": 2,
    }

    assert parse_mongo_db_arg("123.45.67.89:27017:baz.foo!-123") == {
        "url": "123.45.67.89:27017",
        "db_name": "baz",
        "collection": "foo",
        "priority": -123,
    }
