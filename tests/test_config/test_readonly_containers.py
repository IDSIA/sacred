import pytest
from copy import copy, deepcopy

from sacred.config.custom_containers import make_read_only, ReadOnlyList, ReadOnlyDict
from sacred.utils import SacredError


def _check_read_only_dict(d):
    assert isinstance(d, ReadOnlyDict)

    raises_dict = pytest.raises(SacredError, match="This ReadOnlyDict is read-only!")

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
        d["abcdefg"] = 42

    # Test other functions that modify the dict
    with raises_dict:
        d.clear()

    with raises_dict:
        d.update({"abcdefg": 42})

    with raises_dict:
        d.popitem()

    with raises_dict:
        d.setdefault("a", 0)


def _check_read_only_list(lst):
    assert isinstance(lst, ReadOnlyList)

    raises_list = pytest.raises(SacredError, match="This ReadOnlyList is read-only!")

    if len(lst):
        with raises_list:
            del lst[0]

        with raises_list:
            lst[0] = 42

        with raises_list:
            lst.pop(0)

    with raises_list:
        lst.pop()

    with raises_list:
        lst.clear()

    with raises_list:
        lst.append(42)

    with raises_list:
        lst.extend([1, 2, 3, 4])

    with raises_list:
        lst.insert(0, 0)

    with raises_list:
        lst.remove(1)

    with raises_list:
        lst.sort()

    with raises_list:
        lst.reverse()


def test_readonly_dict():
    d = dict(a=1, b=2, c=3)
    d = make_read_only(d)
    _check_read_only_dict(d)


def test_nested_readonly_dict():
    d = dict(a=1, b=dict(c=3))
    d = make_read_only(d)
    _check_read_only_dict(d)
    _check_read_only_dict(d["b"])


def test_readonly_list():
    lst = [1, 2, 3, 4]
    lst = make_read_only(lst)
    _check_read_only_list(lst)


def test_nested_readonly_list():
    lst = [1, [2, [3, [4]]]]
    lst = make_read_only(lst)
    _check_read_only_list(lst)
    _check_read_only_list(lst[1])
    _check_read_only_list(lst[1][1])
    _check_read_only_list(lst[1][1][1])


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


def test_copy_on_readonly_dict():
    d = dict(a=1, b=2, c=3)
    d = make_read_only(d)
    copied_d = copy(d)
    for (k, v), (k_copied, v_copied) in zip(
        sorted(d.items()), sorted(copied_d.items())
    ):
        assert k == k_copied
        assert v == v_copied


def test_copy_on_nested_readonly_dict():
    d = dict(a=1, b=dict(c=3))
    d = make_read_only(d)
    copied_d = copy(d)
    for (k, v), (k_copied, v_copied) in zip(
        sorted(d.items()), sorted(copied_d.items())
    ):
        assert k == k_copied
        assert v == v_copied


def test_copy_on_nested_readonly_dict_still_raises():
    d = dict(a=1, b=dict(c=3))
    d = make_read_only(d)
    copied_d = copy(d)
    with pytest.raises(SacredError):
        copied_d["b"]["c"] = 4


def test_deepcopy_on_readonly_dict():
    d = dict(a=1, b=2, c=3)
    d = make_read_only(d)
    copied_d = deepcopy(d)
    for (k, v), (k_copied, v_copied) in zip(
        sorted(d.items()), sorted(copied_d.items())
    ):
        assert k == k_copied
        assert v == v_copied


def test_deepcopy_on_nested_readonly_dict():
    d = dict(a=1, b=dict(c=3))
    d = make_read_only(d)
    copied_d = deepcopy(d)
    for (k, v), (k_copied, v_copied) in zip(
        sorted(d.items()), sorted(copied_d.items())
    ):
        assert k == k_copied
        assert v == v_copied


def test_deepcopy_on_nested_readonly_dict_can_be_mutated():
    d = dict(a=1, b=dict(c=3))
    d = make_read_only(d)
    copied_d = deepcopy(d)
    copied_d["b"]["c"] = 4
    assert d["b"]["c"] != copied_d["b"]["c"]


def test_copy_on_readonly_list():
    lst = [1, 2, 3, 4]
    lst = make_read_only(lst)
    lst = make_read_only(lst)
    copied_l = copy(lst)
    for v, v_copied in zip(lst, copied_l):
        assert v == v_copied


def test_copy_on_nested_readonly_list():
    lst = [1, [2, [3, [4]]]]
    lst = make_read_only(lst)
    copied_l = copy(lst)
    for v, v_copied in zip(lst, copied_l):
        assert v == v_copied


def test_copy_on_nested_readonly_dict_still_list():
    lst = [1, [2, [3, [4]]]]
    lst = make_read_only(lst)
    copied_l = copy(lst)
    with pytest.raises(SacredError):
        copied_l[1][1].append(5)


def test_deepcopy_on_readonly_list():
    lst = [1, 2, 3, 4]
    lst = make_read_only(lst)
    lst = make_read_only(lst)
    copied_l = deepcopy(lst)
    for v, v_copied in zip(lst, copied_l):
        assert v == v_copied


def test_deepcopy_on_nested_readonly_list():
    lst = [1, [2, [3, [4]]]]
    lst = make_read_only(lst)
    copied_l = deepcopy(lst)
    for v, v_copied in zip(lst, copied_l):
        assert v == v_copied


def test_deepcopy_on_nested_readonly_list_can_be_mutated():
    lst = [1, [2, [3, [4]]]]
    lst = make_read_only(lst)
    copied_l = deepcopy(lst)
    copied_l[1][1].append(5)
    assert lst[1][1] != copied_l[1][1]
