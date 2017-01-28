import wrapt


class ContextDecorator(object):
    """A base class enabling context managers to work as decorators."""

    def _recreate_cm(self):
        """Return a recreated instance of self.

        Allows an otherwise one-shot context manager like
        _GeneratorContextManager to support use as
        a decorator via implicit recreation.

        This is a private interface just for _GeneratorContextManager.
        See issue #11647 (https://bugs.python.org/issue11647) for details.
        """
        return self

    @wrapt.decorator
    def __call__(self, wrapped, instance, args, kwargs):
        with self._recreate_cm():
            return wrapped(*args, **kwargs)
