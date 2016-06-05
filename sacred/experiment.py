#!/usr/bin/env python
# coding=utf-8
"""This module defines the Experiment class, which is central to sacred."""
from __future__ import division, print_function, unicode_literals

import inspect
import sys
from collections import OrderedDict

from sacred.arg_parser import get_config_updates, parse_args
from sacred.commandline_options import gather_command_line_options, ForceOption
from sacred.commands import print_config, print_dependencies
from sacred.ingredient import Ingredient
from sacred.utils import print_filtered_stacktrace

__sacred__ = True  # marks files that should be filtered from stack traces

__all__ = ('Experiment',)


class Experiment(Ingredient):
    """
    The central class for each experiment in Sacred.

    It manages the configuration, the main function, captured methods,
    observers, commands, and further ingredients.

    An Experiment instance should be created as one of the first
    things in any experiment-file.
    """

    def __init__(self, name, ingredients=(), interactive=False):
        """
        Create a new experiment with the given name and optional ingredients.

        Parameters
        ----------
        name : str
            The name of this experiment.

        ingredients : list[sacred.Ingredient]
            A list of ingredients to be used with this experiment.

        interactive : bool
            If set to True will allow the experiment to be run in interactive
            mode (e.g. IPython or Jupyter notebooks).
            However, this mode is discouraged since it won't allow storing the
            source-code or reliable reproduction of the runs.
        """
        caller_globals = inspect.stack()[1][0].f_globals
        super(Experiment, self).__init__(path=name,
                                         ingredients=ingredients,
                                         interactive=interactive,
                                         _caller_globals=caller_globals)
        self.default_command = ""
        self.command(print_config, unobserved=True)
        self.command(print_dependencies, unobserved=True)
        self.observers = []
        self.current_run = None
        self.captured_out_filter = None
        """Filter function to be applied to captured output of a run"""

    # =========================== Decorators ==================================

    def main(self, function):
        """
        Decorator to define the main function of the experiment.

        The main function of an experiment is the default command that is being
        run when no command is specified, or when calling the run() method.

        Usually it is more convenient to use ``automain`` instead.
        """
        captured = self.command(function)
        self.default_command = captured.__name__
        return captured

    def automain(self, function):
        """
        Decorator that defines *and runs* the main function of the experiment.

        The decorated function is marked as the default command for this
        experiment, and the command-line interface is automatically run when
        the file is executed.

        The method decorated by this should be last in the file because is
        equivalent to:

        .. code-block:: python

            @ex.main
            def my_main():
                pass

            if __name__ == '__main__':
                ex.run_commandline()
        """
        captured = self.main(function)
        if function.__module__ == '__main__':
            # Ensure that automain is not used in interactive mode.
            import inspect
            main_filename = inspect.getfile(function)
            if (main_filename == '<stdin>' or
                    (main_filename.startswith('<ipython-input-') and
                     main_filename.endswith('>'))):
                raise RuntimeError('Cannot use @ex.automain decorator in '
                                   'interactive mode. Use @ex.main instead.')

            self.run_commandline()
        return captured

    # =========================== Public Interface ============================

    def run(self, config_updates=None, named_configs=()):
        """
        Run the main function of the experiment.

        Parameters
        ----------
        config_updates : dict
            Changes to the configuration as a nested dictionary

        named_configs : list[str]
            list of names of named_configs to use

        Returns
        -------
        sacred.run.Run
            the Run object corresponding to the finished run
        """
        assert self.default_command, "No main function found"
        return self.run_command(self.default_command,
                                config_updates=config_updates,
                                named_configs=named_configs)

    def run_command(self, command_name, config_updates=None,
                    named_configs=(), args=()):
        """Run the command with the given name.

        Parameters
        ----------
        command_name : str
            Name of the command to be run.

        config_updates : dict
            A dictionary of parameter values that should be updates. (optional)

        named_configs : list[str]
            List of names of named configurations to use. (optional)

        args : dict
            Dictionary of command-line options.

        Returns
        -------
        sacred.run.Run
            The Run object corresponding to the finished run.
        """
        force_flag = '--' + ForceOption.get_flag()[1]
        force = args[force_flag] if force_flag in args else False

        run = self._create_run_for_command(command_name, config_updates,
                                           named_configs, force=force)
        self.current_run = run

        for option in gather_command_line_options():
            op_name = '--' + option.get_flag()[1]
            if op_name in args and args[op_name]:
                option.apply(args[op_name], run)
        self.current_run.run_logger.info("Running command '%s'", command_name)
        run()
        self.current_run = None
        return run

    def run_commandline(self, argv=None):
        """
        Run the command-line interface of this experiment.

        If ``argv`` is omitted it defaults to ``sys.argv``.

        Parameters
        ----------
        argv : list[str]
            Split command-line like ``sys.argv``.

        Returns
        -------
        sacred.run.Run
            The Run object corresponding to the finished run.
        """
        if argv is None:
            argv = sys.argv
        all_commands = self.gather_commands()

        args = parse_args(argv,
                          description=self.doc,
                          commands=OrderedDict(all_commands))
        config_updates, named_configs = get_config_updates(args['UPDATE'])
        cmd_name = args.get('COMMAND') or self.default_command

        try:
            return self.run_command(cmd_name, config_updates, named_configs,
                                    args)
        except Exception:
            if not self.current_run or self.current_run.debug:
                raise
            elif self.current_run.pdb:
                import traceback
                import pdb
                traceback.print_exception(*sys.exc_info())
                pdb.post_mortem()
            else:
                print_filtered_stacktrace()

    def open_resource(self, filename):
        """Open a file and also save it as a resource.

        Opens a file, reports it to the observers as a resource, and returns
        the opened file.

        In Sacred terminology a resource is a file that the experiment needed
        to access during a run. In case of a MongoObserver that means making
        sure the file is stored in the database (but avoiding duplicates) along
        its path and md5 sum.

        This function can only be called during a run, and just calls the
        :py:meth:`sacred.run.Run.open_resource` method.

        Parameters
        ----------
        filename: str
            name of the file that should be opened

        Returns
        -------
        file
            the opened file-object
        """
        assert self.current_run is not None, "Can only be called during a run."
        return self.current_run.open_resource(filename)

    def add_artifact(self, filename):
        """Add a file as an artifact.

        In Sacred terminology an artifact is a file produced by the experiment
        run. In case of a MongoObserver that means storing the file in the
        database.

        This function can only be called during a run, and just calls the
        :py:meth:`sacred.run.Run.add_artifact` method.

        Parameters
        ----------
        filename : str
            name of the file to be stored as artifact
        """
        assert self.current_run is not None, "Can only be called during a run."
        self.current_run.add_artifact(filename)

    @property
    def info(self):
        """Access the info-dict for storing custom information.

        Only works during a run and is essentially a shortcut to:

        .. code-block:: python

            @ex.capture
            def my_captured_function(_run):
                # [...]
                _run.info   # == ex.info
        """
        return self.current_run.info

    def gather_commands(self):
        for cmd_name, cmd in self.commands.items():
            yield cmd_name, cmd

        for ingred in self.ingredients:
            for cmd_name, cmd in ingred.gather_commands():
                yield cmd_name, cmd
