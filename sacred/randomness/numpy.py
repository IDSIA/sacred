from .save_state import SaveState


def set_numpy_seed(seed):
    import numpy as np

    np.random.seed(seed)


def get_state():
    import numpy as np

    return np.random.get_state()


def set_state(state):
    import numpy as np

    np.random.set_state(state)


def save_numpy_random_state(function_to_wrap=None):
    return SaveState(get_state, set_state, function_to_wrap)
