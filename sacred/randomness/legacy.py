import random

import sacred
import sacred.optional as opt
from sacred.utils import module_is_in_cache
from sacred import randomness


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
    sacred.randomness.python.set_seed(seed)
    if opt.has_numpy:
        sacred.randomness.numpy.set_seed(seed)
    if module_is_in_cache("tensorflow"):
        sacred.randomness.tensorflow.set_seed()
    if module_is_in_cache("torch"):
        sacred.randomness.torch.set_seed()
