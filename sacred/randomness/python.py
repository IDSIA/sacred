import random
from .save_state import SaveState


def set_python_random_seed(seed):
    random.seed(seed)


def get_state():
    return random.getstate()


def set_state(state):
    random.setstate(state)


def save_python_random_state(function_to_wrap=None):
    return SaveState(get_state, set_state, function_to_wrap)
