import pytest

from sacred.config.custom_containers import make_read_only, ReadOnlyList, \
    ReadOnlyDict
from sacred.utils import SacredError


def _check_read_only_dict(d):
    assert isinstance(d, ReadOnlyDict)

    raises_dict = pytest.raises(
        SacredError, match='This ReadOnlyDict is read-only!')

    if len(d) > 0:
        # Test removal of entries and overwrite an already present entry
        key = list(d.keys())[0]

        with raises_dict:
            d[key] = 42

        with raises_dict:
            del d[key]

        with raises_dict:
            d.pop(key)

    # Test direct writes
    with raises_dict:
        d['abcdefg'] = 42

    # Test other functions that modify the dict
    with raises_dict:
        d.clear()

    with raises_dict:
        d.update({'abcdefg': 42})

    with raises_dict:
        d.popitem()

    with raises_dict:
        d.setdefault('a', 0)


def _check_read_only_list(l):
    assert isinstance(l, ReadOnlyList)

    raises_list = pytest.raises(
        SacredError, match='This ReadOnlyList is read-only!')

    if len(l):
        with raises_list:
            del l[0]

        with raises_list:
            l[0] = 42

        with raises_list:
            l.pop(0)

    with raises_list:
        l.pop()

    with raises_list:
        l.clear()

    with raises_list:
        l.append(42)

    with raises_list:
        l.extend([1, 2, 3, 4])

    with raises_list:
        l.insert(0, 0)

    with raises_list:
        l.remove(1)

    with raises_list:
        l.sort()

    with raises_list:
        l.reverse()


def test_readonly_dict():
    d = dict(a=1, b=2, c=3)
    d = make_read_only(d)
    _check_read_only_dict(d)


def test_nested_readonly_dict():
    d = dict(a=1, b=dict(c=3))
    d = make_read_only(d)
    _check_read_only_dict(d)
    _check_read_only_dict(d['b'])


def test_readonly_list():
    l = [1, 2, 3, 4]
    l = make_read_only(l)
    _check_read_only_list(l)


def test_nested_readonly_list():
    l = [1, [2, [3, [4]]]]
    l = make_read_only(l)
    _check_read_only_list(l)
    _check_read_only_list(l[1])
    _check_read_only_list(l[1][1])
    _check_read_only_list(l[1][1][1])


def test_nested_readonly_containers():
    container = ([0, [], {}, ()], {0: (), 1: [], 2: {}})
    container = make_read_only(container)
    _check_read_only_list(container[0])
    _check_read_only_list(container[0][1])
    _check_read_only_dict(container[0][2])
    _check_read_only_dict(container[1])
    _check_read_only_dict(container[1][2])
    _check_read_only_list(container[1][1])

    # Check explicitly for tuple (and not isinstance) to be sure that the type
    # is not altered
    assert type(container) == tuple
    assert type(container[0][3]) == tuple
    assert type(container[1][0]) == tuple
