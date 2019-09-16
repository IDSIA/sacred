from sacred.config.default_args import get_default_args


def dodo(dudu=4885, dada=[8485, 545]):
    """Example function with types documented in the docstring.

    `PEP 484`_ type annotations are supported. If attribute, parameter, and
    return types are annotated according to `PEP 484`_, they do not need to be
    included in the docstring:

    Args:
        dudu (int): First parameter.
            Second line.
        dada (list): The second parameter.

    Returns:
        bool: The return value. True for success, False otherwise.

    .. _PEP 484:
        https://www.python.org/dev/peps/pep-0484/

    """
    pass


def test_get_default_args():
    default_args = get_default_args(dodo)

    assert default_args["dudu"].value == 4885
    assert default_args["dudu"].type_ == "int"
    assert default_args["dudu"].description == "First parameter.\nSecond line."

    assert default_args["dada"].value == [8485, 545]
    assert default_args["dada"].type_ == "list"
    assert default_args["dada"].description == "The second parameter."
