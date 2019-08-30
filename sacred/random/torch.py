from .save_state import SaveState


def set_torch_seed(seed):
    import torch

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_state():
    import torch

    state = [torch.get_rng_state()]
    if torch.cuda.is_available():
        state.append(torch.cuda.random.get_rng_state_all())
    return state


def set_state(state):
    import torch

    torch.set_rng_state(state[0])
    if torch.cuda.is_available():
        torch.cuda.random.set_rng_state_all(state[1])


def save_torch_random_state(function_to_wrap=None):
    return SaveState(get_state, set_state, function_to_wrap)
