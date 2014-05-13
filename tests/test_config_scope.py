#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import pytest
from sacred.config_scope import ConfigScope, DogmaticDict, DogmaticList


########################  Tests  ###############################################

# noinspection PyUnresolvedReferences,PyUnusedLocal,PyMethodMayBeStatic
class TestConfigScope(object):
    @pytest.fixture
    def conf_scope(self):
        @ConfigScope
        def cfg():
            a = 1
            b = 2.0
            c = True
            d = 'string'
            e = [1, 2, 3]
            f = {'a': 'b', 'c': 'd'}
            composit1 = a + b
            composit2 = f['c'] + "ada"

            ignored1 = lambda: 23

            deriv = ignored1()

            def ignored2():
                pass

            ignored3 = int

        cfg()
        return cfg

    def test_config_scope_is_dict(self, conf_scope):
        assert isinstance(conf_scope, ConfigScope)
        assert isinstance(conf_scope, dict)

    def test_config_scope_contains_keys(self, conf_scope):
        assert set(conf_scope.keys()) == {'a', 'b', 'c', 'd', 'e', 'f', 'composit1', 'composit2', 'deriv'}

        assert conf_scope['a'] == 1
        assert conf_scope['b'] == 2.0
        assert conf_scope['c']
        assert conf_scope['d'] == 'string'
        assert conf_scope['e'] == [1, 2, 3]
        assert conf_scope['f'] == {'a': 'b', 'c': 'd'}
        assert conf_scope['composit1'] == 3.0
        assert conf_scope['composit2'] == 'dada'
        assert conf_scope['deriv'] == 23

    def test_fixing_values(self, conf_scope):
        conf_scope({'a': 100})
        assert conf_scope['a'] == 100
        assert conf_scope['composit1'] == 102.0

    def test_fixing_nested_dicts(self, conf_scope):
        conf_scope({'f': {'c': 't'}})
        assert conf_scope['f']['a'] == 'b'
        assert conf_scope['f']['c'] == 't'
        assert conf_scope['composit2'] == 'tada'


# noinspection PyMethodMayBeStatic
class TestDogmaticDict(object):
    def test_isinstance_of_dict(self):
        assert isinstance(DogmaticDict(), dict)

    def test_dict_interface(self):
        d = DogmaticDict()
        assert d == {}
        d['a'] = 12
        d['b'] = 'foo'
        assert 'a' in d
        assert 'b' in d

        assert d['a'] == 12
        assert d['b'] == 'foo'

        assert set(d.keys()) == {'a', 'b'}
        assert set(d.values()) == {12, 'foo'}
        assert set(d.items()) == {('a', 12), ('b', 'foo')}

        del d['a']
        assert 'a' not in d

        d['b'] = 'bar'
        assert d['b'] == 'bar'

        d.update({'a': 1, 'c': 2})
        assert d['a'] == 1
        assert d['b'] == 'bar'
        assert d['c'] == 2

        d.update(a=2, b=3)
        assert d['a'] == 2
        assert d['b'] == 3
        assert d['c'] == 2

        d.update([('b', 9), ('c', 7)])
        assert d['a'] == 2
        assert d['b'] == 9
        assert d['c'] == 7

    def test_fixed_value_not_initialized(self):
        d = DogmaticDict({'a': 7})
        assert 'a' not in d

    def test_fixed_value_fixed(self):
        d = DogmaticDict({'a': 7})
        d['a'] = 8
        assert d['a'] == 7

        del d['a']
        assert 'a' in d
        assert d['a'] == 7

        d.update([('a', 9), ('b', 12)])
        assert d['a'] == 7

        d.update({'a': 9, 'b': 12})
        assert d['a'] == 7

        d.update(a=10, b=13)
        assert d['a'] == 7

    def test_revelation(self):
        d = DogmaticDict({'a': 7, 'b': 12})
        d['b'] = 23
        assert 'a' not in d
        m = d.revelation()
        assert set(m) == {'a'}
        assert 'a' in d


# noinspection PyMethodMayBeStatic
class TestDogmaticList(object):
    def test_isinstance_of_list(self):
        assert isinstance(DogmaticList(), list)

    def test_init(self):
        l = DogmaticList()
        assert l == []

        l2 = DogmaticList([2, 3, 1])
        assert l2 == [2, 3, 1]

    def test_append(self):
        l = DogmaticList([1, 2])
        l.append(3)
        l.append(4)
        assert l == [1, 2]

    def test_extend(self):
        l = DogmaticList([1, 2])
        l.extend([3, 4])
        assert l == [1, 2]

    def test_insert(self):
        l = DogmaticList([1, 2])
        l.insert(1, 17)
        assert l == [1, 2]

    def test_pop(self):
        l = DogmaticList([1, 2, 3])
        with pytest.raises(TypeError):
            l.pop()
        assert l == [1, 2, 3]

    def test_sort(self):
        l = DogmaticList([3, 1, 2])
        l.sort()
        assert l == [3, 1, 2]

    def test_reverse(self):
        l = DogmaticList([1, 2, 3])
        l.reverse()
        assert l == [1, 2, 3]

    def test_setitem(self):
        l = DogmaticList([1, 2, 3])
        l[1] = 23
        assert l == [1, 2, 3]

    def test_setslice(self):
        l = DogmaticList([1, 2, 3])
        l[1:3] = [4, 5]
        assert l == [1, 2, 3]

    def test_delitem(self):
        l = DogmaticList([1, 2, 3])
        del l[1]
        assert l == [1, 2, 3]

    def test_delslice(self):
        l = DogmaticList([1, 2, 3])
        del l[1:]
        assert l == [1, 2, 3]

    def test_iadd(self):
        l = DogmaticList([1, 2])
        l += [3, 4]
        assert l == [1, 2]

    def test_imul(self):
        l = DogmaticList([1, 2])
        l *= 4
        assert l == [1, 2]

    def test_list_interface_getitem(self):
        l = DogmaticList([0, 1, 2])
        assert l[0] == 0
        assert l[1] == 1
        assert l[2] == 2

        assert l[-1] == 2
        assert l[-2] == 1
        assert l[-3] == 0

    def test_list_interface_len(self):
        l = DogmaticList()
        assert len(l) == 0
        l = DogmaticList([0, 1, 2])
        assert len(l) == 3

    def test_list_interface_count(self):
        l = DogmaticList([1, 2, 4, 4, 5])
        assert l.count(1) == 1
        assert l.count(3) == 0
        assert l.count(4) == 2

    def test_list_interface_index(self):
        l = DogmaticList([1, 2, 4, 4, 5])
        assert l.index(1) == 0
        assert l.index(4) == 2
        assert l.index(5) == 4
        with pytest.raises(ValueError):
            l.index(3)
