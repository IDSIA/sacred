#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import random
from six import integer_types
import sacred.optional as opt

__sacred__ = True  # marks files that should be filtered from stack traces

SEEDRANGE = (1, int(1e9))


def get_seed(rnd=None):
    if rnd is None:
        return random.randint(*SEEDRANGE)
    return rnd.randint(*SEEDRANGE)


def create_rnd(seed):
    assert isinstance(seed, integer_types), \
        "Seed has to be integer but was %s %s" % (repr(seed), type(seed))
    if opt.has_numpy:
        return opt.np.random.RandomState(seed)
    else:
        return random.Random(seed)


def set_global_seed(seed):
    random.seed(seed)
    if opt.has_numpy:
        opt.np.random.seed(seed)
