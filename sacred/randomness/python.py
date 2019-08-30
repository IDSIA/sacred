import random


def set_seed(seed):
    random.seed(seed)


def get_state():
    return random.getstate()


def set_state(state):
    random.setstate(state)
