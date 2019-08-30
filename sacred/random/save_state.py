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
