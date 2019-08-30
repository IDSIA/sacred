import torch


def set_seed(seed):

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_state():
    state = [torch.get_rng_state()]
    if torch.cuda.is_available():
        state.append(torch.cuda.random.get_rng_state_all())
    return state


def set_state(state):
    torch.set_rng_state(state[0])
    if torch.cuda.is_available():
        torch.cuda.random.set_rng_state_all(state[1])
