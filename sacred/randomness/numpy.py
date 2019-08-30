import numpy as np


def set_seed(seed):
    np.random.seed(seed)


def get_state():
    return np.random.get_state()


def set_state(state):
    np.random.set_state(state)
