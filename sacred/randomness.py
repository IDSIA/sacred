#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals

import random

import sacred.optional as opt
from sacred.utils import module_is_in_cache, get_package_version, parse_version, int_types

SEEDRANGE = (1, int(1e9))


def get_seed(rnd=None):
    if rnd is None:
        return random.randint(*SEEDRANGE)
    return rnd.randint(*SEEDRANGE)


def create_rnd(seed):
    assert isinstance(seed, int_types), \
        "Seed has to be integer but was {} {}".format(repr(seed), type(seed))
    if opt.has_numpy:
        return opt.np.random.RandomState(seed)
    else:
        return random.Random(seed)


def set_global_seed(seed):
    random.seed(seed)
    if opt.has_numpy:
        opt.np.random.seed(seed)
    if module_is_in_cache('tensorflow'):
        # Ensures backward and forward compatibility with TensorFlow 1 and 2.
        if get_package_version('tensorflow') < parse_version('1.13.1'):
            import warnings
            warnings.warn("Use of TensorFlow 1.12 and older is deprecated. "
                          "Use Tensorflow 1.13 or newer instead.", DeprecationWarning)
            import tensorflow as tf
        else:
            import tensorflow.compat.v1 as tf
        tf.set_random_seed(seed)
    if module_is_in_cache('torch'):
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
