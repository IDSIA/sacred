#!/usr/bin/env python
# coding=utf-8

import random

import sacred.optional as opt
from sacred.utils import module_is_in_cache

SEEDRANGE = (1, int(1e9))


def get_seed(rnd=None):
    if rnd is None:
        return random.randint(*SEEDRANGE)
    return rnd.randint(*SEEDRANGE)


def create_rnd(seed):
    assert isinstance(seed, int), "Seed has to be integer but was {} {}".format(
        repr(seed), type(seed)
    )
    if opt.has_numpy:
        return opt.np.random.RandomState(seed)
    else:
        return random.Random(seed)


def set_global_seed(seed):
    set_python_random_seed(seed)
    if opt.has_numpy:
        set_numpy_seed(seed)
    if module_is_in_cache("tensorflow"):
        set_tensorflow_seed(seed)
    if module_is_in_cache("torch"):
        set_torch_seed(seed)


def set_python_random_seed(seed):
    random.seed(seed)


def set_numpy_seed(seed):
    import numpy as np

    np.random.seed(seed)


def set_tensorflow_seed(seed):
    tf = opt.get_tensorflow()
    tf.set_random_seed(seed)


def set_torch_seed(seed):
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class SaveState:
    def __init__(self, get_state_function, set_state_function, function_to_wrap=None):
        """Can be used as a decorator or a context manager."""
        self.get_state = get_state_function
        self.set_state = set_state_function
        self.function_to_wrap = function_to_wrap
        self.state = None

    def __enter__(self):
        self.state = self.get_state()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.set_state(self.state)

    def __call__(self, *args, **kwargs):
        with self:
            self.function_to_wrap(*args, **kwargs)


def get_python_random_state():
    return random.getstate()


def set_python_random_state(state):
    random.setstate(state)


def save_python_random_state(function_to_wrap=None):
    return SaveState(get_python_random_state, set_python_random_state, function_to_wrap)


def get_numpy_state():
    import numpy as np

    return np.random.get_state()


def set_numpy_state(state):
    import numpy as np

    np.random.set_state(state)


def save_numpy_random_state(function_to_wrap=None):
    return SaveState(get_numpy_state, set_numpy_state, function_to_wrap)
