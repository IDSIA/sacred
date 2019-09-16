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

    assert default_args[0].name == "dudu"
    assert default_args[0].value == 4885
    assert default_args[0].type_ == "int"
    assert default_args[0].description == "First parameter.\nSecond line."

    assert default_args[1].name == "dada"
    assert default_args[1].value == [8485, 545]
    assert default_args[1].type_ == "list"
    assert default_args[1].description == "The second parameter."
