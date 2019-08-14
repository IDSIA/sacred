#!/usr/bin/env python
# coding=utf-8

from sacred import Ingredient

"""Global Docstring"""

from mock import patch
import pytest
import sys

from sacred import cli_option
from sacred import host_info_gatherer
from sacred.experiment import Experiment
from sacred.utils import apply_backspaces_and_linefeeds, ConfigAddedError, SacredError


@pytest.fixture
def ex():
    return Experiment("ator3000")


def test_main(ex):
    @ex.main
    def foo():
        pass

    assert "foo" in ex.commands
    assert ex.commands["foo"] == foo
    assert ex.default_command == "foo"


def test_automain_imported(ex):
    main_called = [False]

    with patch.object(sys, "argv", ["test.py"]):

        @ex.automain
        def foo():
            main_called[0] = True

        assert "foo" in ex.commands
        assert ex.commands["foo"] == foo
        assert ex.default_command == "foo"
        assert main_called[0] is False


def test_automain_script_runs_main(ex):
    global __name__
    oldname = __name__
    main_called = [False]

    try:
        __name__ = "__main__"
        with patch.object(sys, "argv", ["test.py"]):

            @ex.automain
            def foo():
                main_called[0] = True

            assert "foo" in ex.commands
            assert ex.commands["foo"] == foo
            assert ex.default_command == "foo"
            assert main_called[0] is True
    finally:
        __name__ = oldname


def test_fails_on_unused_config_updates(ex):
    @ex.config
    def cfg():
        a = 1
        c = 3

    @ex.main
    def foo(a, b=2):
        return a + b

    # normal config updates work
    assert ex.run(config_updates={"a": 3}).result == 5
    # not in config but used works
    assert ex.run(config_updates={"b": 8}).result == 9
    # unused but in config updates work
    assert ex.run(config_updates={"c": 9}).result == 3

    # unused config updates raise
    with pytest.raises(ConfigAddedError):
        ex.run(config_updates={"d": 3})


def test_fails_on_nested_unused_config_updates(ex):
    @ex.config
    def cfg():
        a = {"b": 1}
        d = {"e": 3}

    @ex.main
    def foo(a):
        return a["b"]

    # normal config updates work
    assert ex.run(config_updates={"a": {"b": 2}}).result == 2
    # not in config but parent is works
    assert ex.run(config_updates={"a": {"c": 5}}).result == 1
    # unused but in config works
    assert ex.run(config_updates={"d": {"e": 7}}).result == 1

    # unused nested config updates raise
    with pytest.raises(ConfigAddedError):
        ex.run(config_updates={"d": {"f": 3}})


def test_considers_captured_functions_for_fail_on_unused_config(ex):
    @ex.config
    def cfg():
        a = 1

    @ex.capture
    def transmogrify(a, b=0):
        return a + b

    @ex.main
    def foo():
        return transmogrify()

    assert ex.run(config_updates={"a": 7}).result == 7
    assert ex.run(config_updates={"b": 3}).result == 4

    with pytest.raises(ConfigAddedError):
        ex.run(config_updates={"c": 3})


def test_considers_prefix_for_fail_on_unused_config(ex):
    @ex.config
    def cfg():
        a = {"b": 1}

    @ex.capture(prefix="a")
    def transmogrify(b):
        return b

    @ex.main
    def foo():
        return transmogrify()

    assert ex.run(config_updates={"a": {"b": 3}}).result == 3

    with pytest.raises(ConfigAddedError):
        ex.run(config_updates={"b": 5})

    with pytest.raises(ConfigAddedError):
        ex.run(config_updates={"a": {"c": 5}})


def test_non_existing_prefix_is_treatet_as_empty_dict(ex):
    @ex.capture(prefix="nonexisting")
    def transmogrify(b=10):
        return b

    @ex.main
    def foo():
        return transmogrify()

    assert ex.run().result == 10


def test_using_a_named_config(ex):
    @ex.config
    def cfg():
        a = 1

    @ex.named_config
    def ncfg():
        a = 10

    @ex.main
    def run(a):
        return a

    assert ex.run().result == 1
    assert ex.run(named_configs=["ncfg"]).result == 10


def test_empty_dict_named_config(ex):
    @ex.named_config
    def ncfg():
        empty_dict = {}
        nested_empty_dict = {"k1": {"k2": {}}}

    @ex.automain
    def main(empty_dict=1, nested_empty_dict=2):
        return empty_dict, nested_empty_dict

    assert ex.run().result == (1, 2)
    assert ex.run(named_configs=["ncfg"]).result == ({}, {"k1": {"k2": {}}})


def test_empty_dict_config_updates(ex):
    @ex.config
    def cfg():
        a = 1

    @ex.config
    def default():
        a = {"b": 1}

    @ex.main
    def main():
        pass

    r = ex.run()
    assert r.config["a"]["b"] == 1


def test_named_config_and_ingredient():
    ing = Ingredient("foo")

    @ing.config
    def cfg():
        a = 10

    ex = Experiment(ingredients=[ing])

    @ex.config
    def default():
        b = 20

    @ex.named_config
    def named():
        b = 30

    @ex.main
    def main():
        pass

    r = ex.run(named_configs=["named"])
    assert r.config["b"] == 30
    assert r.config["foo"] == {"a": 10}


def test_captured_out_filter(ex, capsys):
    @ex.main
    def run_print_mock_progress():
        sys.stdout.write("progress 0")
        sys.stdout.flush()
        for i in range(10):
            sys.stdout.write("\b")
            sys.stdout.write("{}".format(i))
            sys.stdout.flush()

    ex.captured_out_filter = apply_backspaces_and_linefeeds
    # disable logging and set capture mode to python
    options = {"--loglevel": "CRITICAL", "--capture": "sys"}
    with capsys.disabled():
        assert ex.run(options=options).captured_out == "progress 9"


def test_adding_option_hooks(ex):
    @ex.option_hook
    def hook(options):
        pass

    @ex.option_hook
    def hook2(options):
        pass

    assert hook in ex.option_hooks
    assert hook2 in ex.option_hooks


def test_option_hooks_without_options_arg_raises(ex):
    with pytest.raises(KeyError):

        @ex.option_hook
        def invalid_hook(wrong_arg_name):
            pass


def test_config_hook_updates_config(ex):
    @ex.config
    def cfg():
        a = "hello"

    @ex.config_hook
    def hook(config, command_name, logger):
        config.update({"a": "me"})
        return config

    @ex.main
    def foo():
        pass

    r = ex.run()
    assert r.config["a"] == "me"


def test_info_kwarg_updates_info(ex):
    """ Tests that the info kwarg of Experiment.create_run is used to update Run.info
    """

    @ex.automain
    def foo():
        pass

    run = ex.run(info={"bar": "baz"})
    assert "bar" in run.info


def test_info_kwargs_default_behavior(ex):
    """ Tests the default behavior of Experiment.create_run when the info kwarg is not specified.
    """

    @ex.automain
    def foo(_run):
        _run.info["bar"] = "baz"

    run = ex.run()
    assert "bar" in run.info


def test_fails_on_config_write(ex):
    @ex.config
    def cfg():
        a = "hello"
        nested_dict = {"dict": {"dict": 1234, "list": [1, 2, 3, 4]}}
        nested_list = [{"a": 42}, (1, 2, 3, 4), [1, 2, 3, 4]]
        nested_tuple = ({"a": 42}, (1, 2, 3, 4), [1, 2, 3, 4])

    @ex.main
    def main(_config, nested_dict, nested_list, nested_tuple):
        raises_list = pytest.raises(
            SacredError, match="The configuration is read-only in a captured function!"
        )
        raises_dict = pytest.raises(
            SacredError, match="The configuration is read-only in a captured function!"
        )

        print("in main")

        # Test for ReadOnlyDict
        with raises_dict:
            _config["a"] = "world!"

        with raises_dict:
            nested_dict["dict"] = "world!"

        with raises_dict:
            nested_dict["list"] = "world!"

        with raises_dict:
            nested_dict.clear()

        with raises_dict:
            nested_dict.update({"a": "world"})

        # Test ReadOnlyList
        with raises_list:
            nested_dict["dict"]["list"][0] = 1

        with raises_list:
            nested_list[0] = "world!"

        with raises_list:
            nested_dict.clear()

        # Test nested tuple
        with raises_dict:
            nested_tuple[0]["a"] = "world!"

        with raises_list:
            nested_tuple[2][0] = 123

    ex.run()


def test_add_config_dict_chain(ex):
    @ex.config
    def config1():
        """This is my demo configuration"""
        dictnest_cap = {"key_1": "value_1", "key_2": "value_2"}

    @ex.config
    def config2():
        """This is my demo configuration"""
        dictnest_cap = {"key_2": "update_value_2", "key_3": "value3", "key_4": "value4"}

    adict = {"dictnest_dict": {"key_1": "value_1", "key_2": "value_2"}}
    ex.add_config(adict)

    bdict = {
        "dictnest_dict": {
            "key_2": "update_value_2",
            "key_3": "value3",
            "key_4": "value4",
        }
    }
    ex.add_config(bdict)

    @ex.automain
    def run():
        pass

    final_config = ex.run().config
    assert final_config["dictnest_cap"] == {
        "key_1": "value_1",
        "key_2": "update_value_2",
        "key_3": "value3",
        "key_4": "value4",
    }
    assert final_config["dictnest_cap"] == final_config["dictnest_dict"]


def test_additional_gatherers():
    @host_info_gatherer("hello")
    def get_hello():
        return "hello world"

    experiment = Experiment("ator3000", additional_host_info=[get_hello])

    @experiment.main
    def foo():
        pass

    experiment.run()
    assert experiment.current_run.host_info["hello"] == "hello world"


@pytest.mark.parametrize("command_line_option", ["-w", "--warning"])
def test_additional_cli_options_flag(command_line_option):

    executed = [False]

    @cli_option("-w", "--warning", is_flag=True)
    def dummy_option(args, run):
        executed[0] = True

    experiment = Experiment("ator3000", additional_cli_options=[dummy_option])

    @experiment.main
    def foo():
        pass

    experiment.run_commandline([__file__, command_line_option])
    assert executed[0]


@pytest.mark.parametrize("command_line_option", ["-w", "--warning"])
def test_additional_cli_options(command_line_option):

    executed = [False]

    @cli_option("-w", "--warning")
    def dummy_option(args, run):
        executed[0] = args

    experiment = Experiment("ator3000", additional_cli_options=[dummy_option])

    @experiment.main
    def foo():
        pass

    experiment.run_commandline([__file__, command_line_option, "10"])
    assert executed[0] == "10"
