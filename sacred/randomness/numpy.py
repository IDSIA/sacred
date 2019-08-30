import numpy as np
from .save_state import SaveState


def set_numpy_seed(seed):
    np.random.seed(seed)


def get_state():
    return np.random.get_state()


def set_state(state):
    np.random.set_state(state)


def save_numpy_random_state(function_to_wrap=None):
    return SaveState(get_state, set_state, function_to_wrap)
