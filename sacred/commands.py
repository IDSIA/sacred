#!/usr/bin/env python
# coding=utf-8
"""Defines the stock-commands that every sacred experiment ships with."""
import copy

import pprint
import pydoc
import re
from collections import namedtuple, OrderedDict

from colorama import Fore, Style

from sacred.config import save_config_file
from sacred.serializer import flatten
from sacred.utils import PATHCHANGE, iterate_flattened_separately

__all__ = (
    "print_config",
    "print_dependencies",
    "save_config",
    "help_for_command",
    "print_named_configs",
)

COLOR_DIRTY = Fore.RED
COLOR_TYPECHANGED = Fore.RED  # prepend Style.BRIGHT for bold
COLOR_ADDED = Fore.GREEN
COLOR_MODIFIED = Fore.BLUE
COLOR_DOC = Style.DIM
ENDC = Style.RESET_ALL  # '\033[0m'

LEGEND = (
    "("
    + COLOR_MODIFIED
    + "modified"
    + ENDC
    + ", "
    + COLOR_ADDED
    + "added"
    + ENDC
    + ", "
    + COLOR_TYPECHANGED
    + "typechanged"
    + ENDC
    + ", "
    + COLOR_DOC
    + "doc"
    + ENDC
    + ")"
)

ConfigEntry = namedtuple("ConfigEntry", "key value added modified typechanged doc")
PathEntry = namedtuple("PathEntry", "key added modified typechanged doc")


PRINTER = pprint.PrettyPrinter()


def print_config(_run):
    """
    Print the updated configuration and exit.

    Text is highlighted:
      green:  value modified
      blue:   value added
      red:    value modified but type changed
    """
    final_config = _run.config
    config_mods = _run.config_modifications
    print(_format_config(final_config, config_mods))


def _format_named_config(indent, path, named_config):
    indent = " " * indent
    assign = path
    if hasattr(named_config, "__doc__") and named_config.__doc__ is not None:
        doc_string = named_config.__doc__
        if doc_string.strip().count("\n") == 0:
            assign += COLOR_DOC + "   # {}".format(doc_string.strip()) + ENDC
        else:
            doc_string = doc_string.replace("\n", "\n" + indent)
            assign += (
                COLOR_DOC + '\n{}"""{}"""'.format(indent + "  ", doc_string) + ENDC
            )
    return indent + assign


def _format_named_configs(named_configs, indent=2):
    lines = ["Named Configurations (" + COLOR_DOC + "doc" + ENDC + "):"]
    for path, named_config in named_configs.items():
        lines.append(_format_named_config(indent, path, named_config))
    if len(lines) < 2:
        lines.append(" " * indent + "No named configs")
    return "\n".join(lines)


def print_named_configs(ingredient):  # noqa: D202
    """Returns a command that prints named configs recursively.

    The command function prints the available named configs for the
    ingredient and all sub-ingredients and exits.

    Example
    -------
    The output is highlighted:
        white: config names
        grey:  doc
    """

    def print_named_configs():
        """Print the available named configs and exit."""
        named_configs = OrderedDict(ingredient.gather_named_configs())
        print(_format_named_configs(named_configs, 2))

    return print_named_configs


def help_for_command(command):
    """Get the help text (signature + docstring) for a command (function)."""
    help_text = pydoc.text.document(command)
    # remove backspaces
    return re.subn(".\\x08", "", help_text)[0]


def print_dependencies(_run):
    """Print the detected source-files and dependencies."""
    print("Dependencies:")
    for dep in _run.experiment_info["dependencies"]:
        pack, _, version = dep.partition("==")
        print("  {:<20} == {}".format(pack, version))

    print("\nSources:")
    for source, digest in _run.experiment_info["sources"]:
        print("  {:<43}  {}".format(source, digest))

    if _run.experiment_info["repositories"]:
        repos = _run.experiment_info["repositories"]
        print("\nVersion Control:")
        for repo in repos:
            mod = COLOR_DIRTY + "M" if repo["dirty"] else " "
            print("{} {:<43}  {}".format(mod, repo["url"], repo["commit"]) + ENDC)
    print("")


def save_config(_config, _log, config_filename="config.json"):
    """
    Store the updated configuration in a file.

    By default uses the filename "config.json", but that can be changed by
    setting the config_filename config entry.
    """
    # Copy the config to make it mutable
    _config = copy.deepcopy(_config)
    if "config_filename" in _config:
        del _config["config_filename"]
    _log.info('Saving config to "{}"'.format(config_filename))
    save_config_file(flatten(_config), config_filename)


def _iterate_marked(cfg, config_mods):
    for path, value in iterate_flattened_separately(cfg, ["__doc__"]):
        if value is PATHCHANGE:
            yield path, PathEntry(
                key=path.rpartition(".")[2],
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path),
                doc=config_mods.docs.get(path),
            )
        else:
            yield path, ConfigEntry(
                key=path.rpartition(".")[2],
                value=value,
                added=path in config_mods.added,
                modified=path in config_mods.modified,
                typechanged=config_mods.typechanged.get(path),
                doc=config_mods.docs.get(path),
            )


def _format_entry(indent, entry):
    color = ""
    indent = " " * indent
    if entry.typechanged:
        color = COLOR_TYPECHANGED  # red
    elif entry.added:
        color = COLOR_ADDED  # green
    elif entry.modified:
        color = COLOR_MODIFIED  # blue
    if entry.key == "__doc__":
        color = COLOR_DOC  # grey
        doc_string = entry.value.replace("\n", "\n" + indent)
        assign = '{}"""{}"""'.format(indent, doc_string)
    elif isinstance(entry, ConfigEntry):
        assign = indent + entry.key + " = " + PRINTER.pformat(entry.value)
    else:  # isinstance(entry, PathEntry):
        assign = indent + entry.key + ":"
    if entry.doc:
        doc_string = COLOR_DOC + "# " + entry.doc + ENDC
        if len(assign) <= 35:
            assign = "{:<35}  {}".format(assign, doc_string)
        else:
            assign += "    " + doc_string
    end = ENDC if color else ""
    return color + assign + end


def _format_config(cfg, config_mods):
    lines = ["Configuration " + LEGEND + ":"]
    for path, entry in _iterate_marked(cfg, config_mods):
        indent = 2 + 2 * path.count(".")
        lines.append(_format_entry(indent, entry))
    return "\n".join(lines)
