from sacred.stflow.internal import ContextMethodDecorator


def test_context_method_decorator():
    """
    Ensure that ContextMethodDecorator can intercept method calls.
    """

    class FooClass:
        def __init__(self, x):
            self.x = x

        def do_foo(self, y, z):
            print("foo")
            print(y)
            print(z)
            return y * self.x + z

    def decorate_three_times(instance, original_method, original_args, original_kwargs):
        print("three_times")
        print(original_args)
        print(original_kwargs)
        return original_method(instance, *original_args, **original_kwargs) * 3

    with ContextMethodDecorator(FooClass, "do_foo", decorate_three_times):
        foo = FooClass(10)
        assert foo.do_foo(5, 6) == (5 * 10 + 6) * 3
        assert foo.do_foo(5, z=6) == (5 * 10 + 6) * 3
        assert foo.do_foo(y=5, z=6) == (5 * 10 + 6) * 3
    assert foo.do_foo(5, 6) == (5 * 10 + 6)
    assert foo.do_foo(5, z=6) == (5 * 10 + 6)
    assert foo.do_foo(y=5, z=6) == (5 * 10 + 6)

    def decorate_three_times_with_exception(
        instance, original_method, original_args, original_kwargs
    ):
        raise RuntimeError("This should be caught")

    exception = False
    try:
        with ContextMethodDecorator(
            FooClass, "do_foo", decorate_three_times_with_exception
        ):
            foo = FooClass(10)
            this_should_raise_exception = foo.do_foo(5, 6)
    except RuntimeError:
        exception = True
    assert foo.do_foo(5, 6) == (5 * 10 + 6)
    assert exception is True
