#!/usr/bin/env python
# coding=utf-8

import os.path
import os

import mock
import pytest
from sacred.dependencies import (
    PEP440_VERSION_PATTERN,
    PackageDependency,
    Source,
    gather_sources_and_dependencies,
    get_digest,
    get_py_file_if_possible,
    is_local_source,
)
import sacred.optional as opt

TEST_DIRECTORY = os.path.dirname(__file__)
EXAMPLE_SOURCE = os.path.join(TEST_DIRECTORY, "__init__.py")

# The digest below is calculated from the test/__init__.py with only Python shebang and coding-information.
# This type of hard-coding is most probably a quite bad idea.
EXAMPLE_DIGEST = "9e428c0aa58b75ff150c4f625e32af68"


@pytest.mark.parametrize(
    "version",
    [
        "0.9.11",
        "2012.04",
        "1!1.1",
        "17.10a104",
        "43.0rc1",
        "0.9.post3",
        "12.4a22.post8",
        "13.3rc2.dev1515",
        "1.0.dev456",
        "1.0a1",
        "1.0a2.dev456",
        "1.0a12.dev456",
        "1.0a12",
        "1.0b1.dev456",
        "1.0b2",
        "1.0b2.post345.dev456",
        "1.0b2.post345",
        "1.0rc1.dev456",
        "1.0rc1",
        "1.0",
        "1.0.post456.dev34",
        "1.0.post456",
        "1.1.dev1",
    ],
)
def test_pep440_version_pattern(version):
    assert PEP440_VERSION_PATTERN.match(version)


def test_pep440_version_pattern_invalid():
    assert PEP440_VERSION_PATTERN.match("foo") is None
    assert PEP440_VERSION_PATTERN.match("_12_") is None
    assert PEP440_VERSION_PATTERN.match("version 4") is None


@pytest.mark.skipif(os.name == "nt", reason="Weird win bug")
def test_source_get_digest():
    assert get_digest(EXAMPLE_SOURCE) == EXAMPLE_DIGEST


def test_source_create_empty():
    with pytest.raises(ValueError):
        Source.create("")


def test_source_create_non_existing():
    with pytest.raises(ValueError):
        Source.create("doesnotexist.py")


@pytest.mark.skipif(os.name == "nt", reason="Weird win bug")
def test_source_create_py():
    s = Source.create(EXAMPLE_SOURCE)
    assert s.filename == os.path.abspath(EXAMPLE_SOURCE)
    assert s.digest == EXAMPLE_DIGEST


@pytest.mark.skipif(os.name == "nt", reason="Weird win bug")
def test_source_to_json():
    s = Source.create(EXAMPLE_SOURCE)
    assert s.to_json() == (os.path.abspath(EXAMPLE_SOURCE), EXAMPLE_DIGEST)


def test_get_py_file_if_possible_with_py_file():
    assert get_py_file_if_possible(EXAMPLE_SOURCE) == EXAMPLE_SOURCE


def test_get_py_file_if_possible_with_pyc_file():
    assert get_py_file_if_possible(EXAMPLE_SOURCE + "c") == EXAMPLE_SOURCE


def test_source_repr():
    s = Source.create(EXAMPLE_SOURCE)
    assert repr(s) == "<Source: {}>".format(os.path.abspath(EXAMPLE_SOURCE))


def test_get_py_file_if_possible_with_pyc_but_nonexistent_py_file():
    assert get_py_file_if_possible("doesnotexist.pyc") == "doesnotexist.pyc"


def test_package_dependency_create_no_version():
    mod = mock.Mock(spec=[], __name__="testmod")
    pd = PackageDependency.create(mod)
    assert pd.name == "testmod"
    assert pd.version is None


def test_package_dependency_fill_non_missing_version():
    pd = PackageDependency("mymod", "1.2.3rc4")
    pd.fill_missing_version()
    assert pd.version == "1.2.3rc4"


def test_package_dependency_fill_missing_version_unknown():
    pd = PackageDependency("mymod", None)
    pd.fill_missing_version()
    assert pd.version == None


def test_package_dependency_fill_missing_version():
    pd = PackageDependency("pytest", None)
    pd.fill_missing_version()
    assert pd.version == pytest.__version__


def test_package_dependency_repr():
    pd = PackageDependency("pytest", "12.4")
    assert repr(pd) == "<PackageDependency: pytest=12.4>"


def test_gather_sources_and_dependencies():
    from tests.dependency_example import some_func

    main, sources, deps = gather_sources_and_dependencies(
        some_func.__globals__, save_git_info=False
    )
    assert isinstance(main, Source)
    assert isinstance(sources, set)
    assert isinstance(deps, set)
    assert main == Source.create(os.path.join(TEST_DIRECTORY, "dependency_example.py"))
    expected_sources = {
        Source.create(os.path.join(TEST_DIRECTORY, "__init__.py")),
        Source.create(os.path.join(TEST_DIRECTORY, "dependency_example.py")),
        Source.create(os.path.join(TEST_DIRECTORY, "foo", "__init__.py")),
        Source.create(os.path.join(TEST_DIRECTORY, "foo", "bar.py")),
    }
    assert sources == expected_sources

    assert PackageDependency.create(pytest) in deps
    assert PackageDependency.create(mock) in deps
    # If numpy is installed on the test system it will automatically be added
    # as an additional dependency, so test for that:
    if opt.has_numpy:
        assert PackageDependency.create(opt.np) in deps
        assert len(deps) == 3
    else:
        assert len(deps) == 2


def test_custom_base_dir():
    from tests.basedir.my_experiment import some_func

    main, sources, deps = gather_sources_and_dependencies(
        some_func.__globals__, False, TEST_DIRECTORY
    )
    assert isinstance(main, Source)
    assert isinstance(sources, set)
    assert isinstance(deps, set)
    assert main == Source.create(
        os.path.join(TEST_DIRECTORY, "basedir", "my_experiment.py")
    )
    expected_sources = {
        Source.create(os.path.join(TEST_DIRECTORY, "__init__.py")),
        Source.create(os.path.join(TEST_DIRECTORY, "basedir", "__init__.py")),
        Source.create(os.path.join(TEST_DIRECTORY, "basedir", "my_experiment.py")),
        Source.create(os.path.join(TEST_DIRECTORY, "foo", "__init__.py")),
        Source.create(os.path.join(TEST_DIRECTORY, "foo", "bar.py")),
    }
    assert sources == expected_sources


@pytest.mark.parametrize(
    "f_name, mod_name, ex_path, is_local",
    [
        ("./foo.py", "bar", ".", False),
        ("./foo.pyc", "bar", ".", False),
        ("./bar.py", "bar", ".", True),
        ("./bar.pyc", "bar", ".", True),
        ("./venv/py/bar.py", "bar", ".", False),
        ("./venv/py/bar.py", "venv.py.bar", ".", True),
        ("./venv/py/bar.pyc", "venv.py.bar", ".", True),
        ("foo.py", "bar", ".", False),
        ("bar.py", "bar", ".", True),
        ("bar.pyc", "bar", ".", True),
        ("bar.pyc", "some.bar", ".", False),
        ("/home/user/bar.py", "user.bar", "/home/user/", True),
        ("bar/__init__.py", "bar", ".", True),
        ("bar/__init__.py", "foo", ".", False),
        ("/home/user/bar/__init__.py", "home.user.bar", "/home/user/", True),
        ("/home/user/bar/__init__.py", "home.user.foo", "/home/user/", False),
    ],
)
def test_is_local_source(f_name, mod_name, ex_path, is_local):
    assert is_local_source(f_name, mod_name, ex_path) == is_local
