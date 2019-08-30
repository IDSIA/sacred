import sacred


def set_python_random_seed(seed):
    sacred.randomness.python.set_seed(seed)
