"""
Contains the command-line parsing and help for experiments.

The command-line interface of sacred is built on top of ``docopt``, which
constructs a command-line parser from a usage text. Curiously in sacred we
first programmatically generate a usage text and then parse it with ``docopt``.
"""

import ast
import textwrap
import inspect
import re
from shlex import quote

from sacred.serializer import restore
from sacred.settings import SETTINGS
from sacred.utils import set_by_dotted_path
from sacred.commandline_options import CLIOption


__all__ = ("get_config_updates", "format_usage")


USAGE_TEMPLATE = """Usage:
  {program_name} [(with UPDATE...)] [options]
  {program_name} help [COMMAND]
  {program_name} (-h | --help)
  {program_name} COMMAND [(with UPDATE...)] [options]

{description}

Options:
{options}

Arguments:
  COMMAND   Name of command to run (see below for list of commands)
  UPDATE    Configuration assignments of the form foo.bar=17
{arguments}
{commands}"""


def get_config_updates(updates):
    """
    Parse the UPDATES given on the commandline.

    Parameters
    ----------
        updates (list[str]):
            list of update-strings of the form NAME=LITERAL or just NAME.

    Returns
    -------
        (dict, list):
            Config updates and named configs to use

    """
    config_updates = {}
    named_configs = []
    if not updates:
        return config_updates, named_configs
    for upd in updates:
        if upd == "":
            continue
        path, sep, value = upd.partition("=")
        if sep == "=":
            path = path.strip()  # get rid of surrounding whitespace
            value = value.strip()  # get rid of surrounding whitespace
            set_by_dotted_path(config_updates, path, _convert_value(value))
        else:
            named_configs.append(path)
    return config_updates, named_configs


def _format_options_usage(options):
    """
    Format the Options-part of the usage text.

    Parameters
    ----------
        options : list[sacred.commandline_options.CommandLineOption]
            A list of all supported commandline options.

    Returns
    -------
        str
            Text formatted as a description for the commandline options

    """
    options_usage = ""
    for op in options:
        short, long = op.get_flags()
        if op.arg:
            flag = "{short} {arg} {long}={arg}".format(
                short=short, long=long, arg=op.arg
            )
        else:
            flag = "{short} {long}".format(short=short, long=long)

        if isinstance(op, CLIOption):
            doc = op.get_description()
        else:
            # legacy
            doc = inspect.cleandoc(op.__doc__)
        wrapped_description = textwrap.wrap(
            doc, width=79, initial_indent=" " * 32, subsequent_indent=" " * 32
        )
        wrapped_description = "\n".join(wrapped_description).strip()

        options_usage += "  {:28}  {}\n".format(flag, wrapped_description)
    return options_usage


def _format_arguments_usage(options):
    """
    Construct the Arguments-part of the usage text.

    Parameters
    ----------
        options : list[sacred.commandline_options.CommandLineOption]
            A list of all supported commandline options.

    Returns
    -------
        str
            Text formatted as a description of the arguments supported by the
            commandline options.

    """
    argument_usage = ""
    for op in options:
        if op.arg and op.arg_description:
            wrapped_description = textwrap.wrap(
                op.arg_description,
                width=79,
                initial_indent=" " * 12,
                subsequent_indent=" " * 12,
            )
            wrapped_description = "\n".join(wrapped_description).strip()
            argument_usage += "  {:8}  {}\n".format(op.arg, wrapped_description)
    return argument_usage


def _format_command_usage(commands):
    """
    Construct the Commands-part of the usage text.

    Parameters
    ----------
        commands : dict[str, func]
            dictionary of supported commands.
            Each entry should be a tuple of (name, function).

    Returns
    -------
        str
            Text formatted as a description of the commands.

    """
    if not commands:
        return ""
    command_usage = "\nCommands:\n"
    cmd_len = max([len(c) for c in commands] + [8])

    for cmd_name, cmd_doc in commands.items():
        cmd_doc = _get_first_line_of_docstring(cmd_doc)
        command_usage += ("  {:%d}  {}\n" % cmd_len).format(cmd_name, cmd_doc)
    return command_usage


def format_usage(program_name, description, commands=None, options=()):
    """
    Construct the usage text.

    Parameters
    ----------
        program_name : str
            Usually the name of the python file that contains the experiment.
        description : str
            description of this experiment (usually the docstring).
        commands : dict[str, func]
            Dictionary of supported commands.
            Each entry should be a tuple of (name, function).
        options : list[sacred.commandline_options.CommandLineOption]
            A list of all supported commandline options.

    Returns
    -------
        str
            The complete formatted usage text for this experiment.
            It adheres to the structure required by ``docopt``.

    """
    usage = USAGE_TEMPLATE.format(
        program_name=quote(program_name),
        description=description.strip() if description else "",
        options=_format_options_usage(options),
        arguments=_format_arguments_usage(options),
        commands=_format_command_usage(commands),
    )
    return usage


def printable_usage(doc):
    # in python < 2.7 you can't pass flags=re.IGNORECASE
    usage_split = re.split(r"([Uu][Ss][Aa][Gg][Ee]:)", doc)
    return re.split(r"\n\s*\n", "".join(usage_split[1:]))[0].strip()


def _get_first_line_of_docstring(func):
    return textwrap.dedent(func.__doc__ or "").strip().split("\n")[0]


def _convert_value(value):
    """Parse string as python literal if possible and fallback to string."""
    try:
        return restore(ast.literal_eval(value))
    except (ValueError, SyntaxError):
        if SETTINGS.COMMAND_LINE.STRICT_PARSING:
            raise
        # use as string if nothing else worked
        return value
