import functools


class ContextMethodDecorator:
    """A helper ContextManager decorating a method with a custom function."""

    def __init__(self, classx, method_name, decorator_func):
        """
        Create a new context manager decorating a function within its scope.

        This is a helper Context Manager that decorates a method of a class
        with a custom function.
        The decoration is only valid within the scope.
        :param classx: A class (object)
        :param method_name A string name of the method to be decorated
        :param decorator_func: The decorator function is responsible
         for calling the original method.
         The signature should be: func(instance, original_method,
         original_args, original_kwargs)
         when called, instance refers to an instance of classx and the
         original_method refers to the original method object which can be
         called.
         args and kwargs are arguments passed to the method

        """
        self.method_name = method_name
        self.decorator_func = decorator_func
        self.classx = classx
        self.patched_by_me = False

    def __enter__(self):

        self.original_method = getattr(self.classx, self.method_name)
        if not hasattr(
            self.original_method, "sacred_patched%s" % self.__class__.__name__
        ):

            @functools.wraps(self.original_method)
            def decorated(instance, *args, **kwargs):
                return self.decorator_func(instance, self.original_method, args, kwargs)

            setattr(self.classx, self.method_name, decorated)
            setattr(decorated, "sacred_patched%s" % self.__class__.__name__, True)
            self.patched_by_me = True

    def __exit__(self, type, value, traceback):
        if self.patched_by_me:
            # Restore original function
            setattr(self.classx, self.method_name, self.original_method)
