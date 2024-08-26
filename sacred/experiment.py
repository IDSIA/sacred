"""The Experiment class, which is central to sacred."""

import inspect
import os.path
import sys
import warnings
from collections import OrderedDict
from typing import Sequence, Optional, List

from docopt import docopt

from sacred import SETTINGS
from sacred.arg_parser import get_config_updates, format_usage, printable_usage
from sacred import commandline_options
from sacred.commandline_options import CLIOption
from sacred.commands import (
    help_for_command,
    print_config,
    print_dependencies,
    save_config,
    print_named_configs,
)
from sacred.observers.file_storage import file_storage_option
from sacred.observers.s3_observer import s3_option
from sacred.config.signature import Signature
from sacred.ingredient import Ingredient
from sacred.initialize import create_run
from sacred.observers.sql import sql_option
from sacred.observers.tinydb_hashfs import tiny_db_option
from sacred.run import Run
from sacred.host_info import check_additional_host_info, HostInfoGetter
from sacred.utils import (
    print_filtered_stacktrace,
    ensure_wellformed_argv,
    SacredError,
    format_sacred_error,
    PathType,
    get_inheritors,
)
from sacred.observers.mongo import mongo_db_option

__all__ = ("Experiment",)


class Experiment(Ingredient):
    """
    The central class for each experiment in Sacred.

    It manages the configuration, the main function, captured methods,
    observers, commands, and further ingredients.

    An Experiment instance should be created as one of the first
    things in any experiment-file.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        ingredients: Sequence[Ingredient] = (),
        interactive: bool = False,
        base_dir: Optional[PathType] = None,
        additional_host_info: Optional[List[HostInfoGetter]] = None,
        additional_cli_options: Optional[Sequence[CLIOption]] = None,
        save_git_info: bool = True,
    ):
        """
        Create a new experiment with the given name and optional ingredients.

        Parameters
        ----------
        name
            Optional name of this experiment, defaults to the filename.
            (Required in interactive mode)

        ingredients : list[sacred.Ingredient], optional
            A list of ingredients to be used with this experiment.

        interactive
            If set to True will allow the experiment to be run in interactive
            mode (e.g. IPython or Jupyter notebooks).
            However, this mode is discouraged since it won't allow storing the
            source-code or reliable reproduction of the runs.

        base_dir
            Optional full path to the base directory of this experiment. This
            will set the scope for automatic source file discovery.

        additional_host_info
            Optional dictionary containing as keys the names of the pieces of
            host info you want to collect, and as
            values the functions collecting those pieces of information.

        save_git_info:
            Optionally save the git commit hash and the git state
            (clean or dirty) for all source files. This requires the GitPython
            package.
        """
        self.additional_host_info = additional_host_info or []
        check_additional_host_info(self.additional_host_info)
        self.additional_cli_options = additional_cli_options or []
        self.all_cli_options = (
            gather_command_line_options() + self.additional_cli_options
        )
        caller_globals = inspect.stack()[1][0].f_globals
        if name is None:
            if interactive:
                raise RuntimeError("name is required in interactive mode.")
            mainfile = caller_globals.get("__file__")
            if mainfile is None:
                raise RuntimeError(
                    "No main-file found. Are you running in "
                    "interactive mode? If so please provide a "
                    "name and set interactive=True."
                )
            name = os.path.basename(mainfile)
            if name.endswith(".py"):
                name = name[:-3]
            elif name.endswith(".pyc"):
                name = name[:-4]
        super().__init__(
            path=name,
            ingredients=ingredients,
            interactive=interactive,
            base_dir=base_dir,
            _caller_globals=caller_globals,
            save_git_info=save_git_info,
        )
        self.default_command = None
        self.command(print_config, unobserved=True)
        self.command(print_dependencies, unobserved=True)
        self.command(save_config, unobserved=True)
        self.command(print_named_configs(self), unobserved=True)
        self.observers = []
        self.current_run = None
        self.captured_out_filter = None
        """Filter function to be applied to captured output of a run"""
        self.option_hooks = []

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

        Example
        -------
        ::

            @ex.main
            def my_main():
                pass

            if __name__ == '__main__':
                ex.run_commandline()
        """
        captured = self.main(function)
        if function.__module__ == "__main__":
            # Ensure that automain is not used in interactive mode.
            import inspect

            main_filename = inspect.getfile(function)
            if main_filename == "<stdin>" or (
                main_filename.startswith("<ipython-input-")
                and main_filename.endswith(">")
            ):
                raise RuntimeError(
                    "Cannot use @ex.automain decorator in "
                    "interactive mode. Use @ex.main instead."
                )

            self.run_commandline()
        return captured

    def option_hook(self, function):
        """
        Decorator for adding an option hook function.

        An option hook is a function that is called right before a run
        is created. It receives (and potentially modifies) the options
        dictionary. That is, the dictionary of commandline options used for
        this run.

        Notes
        -----
        The decorated function MUST have an argument called options.

        The options also contain ``'COMMAND'`` and ``'UPDATE'`` entries,
        but changing them has no effect. Only modification on
        flags (entries starting with ``'--'``) are considered.
        """
        sig = Signature(function)
        if "options" not in sig.arguments:
            raise KeyError(
                "option_hook functions must have an argument called"
                " 'options', but got {}".format(sig.arguments)
            )
        self.option_hooks.append(function)
        return function

    # =========================== Public Interface ============================

    def get_usage(self, program_name=None):
        """Get the commandline usage string for this experiment."""
        program_name = os.path.relpath(
            program_name or sys.argv[0] or "Dummy", self.base_dir
        )
        commands = OrderedDict(self.gather_commands())
        long_usage = format_usage(
            program_name, self.doc, commands, self.all_cli_options
        )
        # internal usage is a workaround because docopt cannot handle spaces
        # in program names. So for parsing we use 'dummy' as the program name.
        # for printing help etc. we want to use the actual program name.
        internal_usage = format_usage("dummy", self.doc, commands, self.all_cli_options)
        short_usage = printable_usage(long_usage)
        return short_usage, long_usage, internal_usage

    def run(
        self,
        command_name: Optional[str] = None,
        config_updates: Optional[dict] = None,
        named_configs: Sequence[str] = (),
        info: Optional[dict] = None,
        meta_info: Optional[dict] = None,
        options: Optional[dict] = None,
    ) -> Run:
        """
        Run the main function of the experiment or a given command.

        Parameters
        ----------
        command_name
            Name of the command to be run. Defaults to main function.

        config_updates
            Changes to the configuration as a nested dictionary

        named_configs
            list of names of named_configs to use

        info
            Additional information for this run.

        meta_info
            Additional meta information for this run.

        options
            Dictionary of options to use

        Returns
        -------
        The Run object corresponding to the finished run.
        """
        run = self._create_run(
            command_name, config_updates, named_configs, info, meta_info, options
        )
        run()
        return run

    def run_commandline(self, argv=None) -> Optional[Run]:
        """
        Run the command-line interface of this experiment.

        If ``argv`` is omitted it defaults to ``sys.argv``.

        Parameters
        ----------
        argv
            Command-line as string or list of strings like ``sys.argv``.

        Returns
        -------
        The Run object corresponding to the finished run.

        """
        argv = ensure_wellformed_argv(argv)
        short_usage, usage, internal_usage = self.get_usage()
        args = docopt(internal_usage, [str(a) for a in argv[1:]], default_help=False)

        cmd_name = args.get("COMMAND") or self.default_command
        config_updates, named_configs = get_config_updates(args["UPDATE"])

        err = self._check_command(cmd_name)
        if not args["help"] and err:
            print(short_usage)
            print(err)
            sys.exit(1)

        if self._handle_help(args, usage):
            sys.exit()

        try:
            return self.run(
                cmd_name,
                config_updates,
                named_configs,
                info={},
                meta_info={},
                options=args,
            )
        except Exception as e:
            if self.current_run:
                debug = self.current_run.debug
            else:
                # The usual command line options are applied after the run
                # object is built completely. Some exceptions (e.g.
                # ConfigAddedError) are raised before this. In these cases,
                # the debug flag must be checked manually.
                debug = args.get("--debug", False)

            if debug:
                # Debug: Don't change behavior, just re-raise exception
                raise
            elif self.current_run and self.current_run.pdb:
                # Print exception and attach pdb debugger
                import traceback
                import pdb

                traceback.print_exception(*sys.exc_info())
                pdb.post_mortem()
            else:
                # Handle pretty printing of exceptions. This includes
                # filtering the stacktrace and printing the usage, as
                # specified by the exceptions attributes
                if isinstance(e, SacredError):
                    print(format_sacred_error(e, short_usage), file=sys.stderr)
                else:
                    print_filtered_stacktrace()
                sys.exit(1)

    def open_resource(self, filename: PathType, mode: str = "r"):
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
        filename
            name of the file that should be opened
        mode
            mode that file will be open

        Returns
        -------
        The opened file-object.
        """
        assert self.current_run is not None, "Can only be called during a run."
        return self.current_run.open_resource(filename, mode)

    def add_resource(self, filename: PathType) -> None:
        """Add a file as a resource.

        In Sacred terminology a resource is a file that the experiment needed
        to access during a run. In case of a MongoObserver that means making
        sure the file is stored in the database (but avoiding duplicates) along
        its path and md5 sum.

        This function can only be called during a run, and just calls the
        :py:meth:`sacred.run.Run.add_resource` method.

        Parameters
        ----------
        filename
            name of the file to be stored as a resource
        """
        assert self.current_run is not None, "Can only be called during a run."
        self.current_run.add_resource(filename)

    def add_artifact(
        self,
        filename: PathType,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """Add a file as an artifact.

        In Sacred terminology an artifact is a file produced by the experiment
        run. In case of a MongoObserver that means storing the file in the
        database.

        This function can only be called during a run, and just calls the
        :py:meth:`sacred.run.Run.add_artifact` method.

        Parameters
        ----------
        filename
            name of the file to be stored as artifact
        name
            optionally set the name of the artifact.
            Defaults to the relative file-path.
        metadata
            optionally attach metadata to the artifact.
            This only has an effect when using the MongoObserver.
        content_type
            optionally attach a content-type to the artifact.
            This only has an effect when using the MongoObserver.
        """
        assert self.current_run is not None, "Can only be called during a run."
        self.current_run.add_artifact(filename, name, metadata, content_type)

    @property
    def info(self) -> dict:
        """Access the info-dict for storing custom information.

        Only works during a run and is essentially a shortcut to:

        Example
        -------
        ::

            @ex.capture
            def my_captured_function(_run):
                # [...]
                _run.info   # == ex.info
        """
        return self.current_run.info

    def log_scalar(self, name: str, value: float, step: Optional[int] = None) -> None:
        """
        Add a new measurement.

        The measurement will be processed by the MongoDB* observer
        during a heartbeat event.
        Other observers are not yet supported.


        Parameters
        ----------
        name
            The name of the metric, e.g. training.loss
        value
            The measured value
        step
            The step number (integer), e.g. the iteration number
            If not specified, an internal counter for each metric
            is used, incremented by one.
        """
        # Method added in change https://github.com/chovanecm/sacred/issues/4
        # The same as Run.log_scalar
        self.current_run.log_scalar(name, value, step)

    def post_process_name(self, name, ingredient):
        if ingredient == self:
            # Removes the experiment's path (prefix) from the names
            # of the gathered items. This means that, for example,
            # 'experiment.print_config' becomes 'print_config'.
            return name[len(self.path) + 1 :]
        return name

    def get_default_options(self) -> dict:
        """Get a dictionary of default options as used with run.

        Returns
        -------
        A dictionary containing option keys of the form '--beat_interval'.
        Their values are boolean if the option is a flag, otherwise None or
        its default value.

        """
        default_options = {}
        for option in self.all_cli_options:
            if isinstance(option, CLIOption):
                if option.is_flag:
                    default_value = False
                else:
                    default_value = None
            else:  # legacy, should be removed later on.
                if option.arg is None:
                    default_value = False
                else:
                    default_value = None
            default_options[option.get_flag()] = default_value

        return default_options

    # =========================== Internal Interface ==========================

    def _create_run(
        self,
        command_name=None,
        config_updates=None,
        named_configs=(),
        info=None,
        meta_info=None,
        options=None,
    ):
        command_name = command_name or self.default_command
        if command_name is None:
            raise RuntimeError(
                "No command found to be run. Specify a command "
                "or define a main function."
            )

        default_options = self.get_default_options()
        if options:
            default_options.update(options)
        options = default_options

        # call option hooks
        for oh in self.option_hooks:
            oh(options=options)

        run = create_run(
            self,
            command_name,
            config_updates,
            named_configs=named_configs,
            force=options.get(commandline_options.force_option.get_flag(), False),
            log_level=options.get(commandline_options.loglevel_option.get_flag(), None),
        )
        if info is not None:
            run.info.update(info)

        run.meta_info["command"] = command_name
        run.meta_info["options"] = options
        run.meta_info["named_configs"] = list(named_configs)
        if config_updates is not None:
            run.meta_info["config_updates"] = config_updates

        if meta_info:
            run.meta_info.update(meta_info)

        options_list = gather_command_line_options() + self.additional_cli_options
        for option in options_list:
            option_value = options.get(option.get_flag(), False)
            if option_value:
                option.apply(option_value, run)

        self.current_run = run
        return run

    def _check_command(self, cmd_name):
        commands = dict(self.gather_commands())
        if cmd_name is not None and cmd_name not in commands:
            return (
                'Error: Command "{}" not found. Available commands are: '
                "{}".format(cmd_name, ", ".join(commands.keys()))
            )

        if cmd_name is None:
            return (
                "Error: No command found to be run. Specify a command"
                " or define main function. Available commands"
                " are: {}".format(", ".join(commands.keys()))
            )

    def _handle_help(self, args, usage):
        if args["help"] or args["--help"]:
            if args["COMMAND"] is None:
                print(usage)
                return True
            else:
                commands = dict(self.gather_commands())
                print(help_for_command(commands[args["COMMAND"]]))
                return True
        return False


def gather_command_line_options(filter_disabled=None):
    """Get a sorted list of all CommandLineOption subclasses."""
    if filter_disabled is None:
        filter_disabled = not SETTINGS.COMMAND_LINE.SHOW_DISABLED_OPTIONS

    options = []
    for opt in get_inheritors(commandline_options.CommandLineOption):
        warnings.warn(
            "Subclassing `CommandLineOption` is deprecated. Please "
            "use the `sacred.cli_option` decorator and pass the function "
            "to the Experiment constructor."
        )
        if filter_disabled and not opt._enabled:
            continue
        options.append(opt)

    options += DEFAULT_COMMAND_LINE_OPTIONS

    return sorted(options, key=commandline_options.get_name)


DEFAULT_COMMAND_LINE_OPTIONS = [
    s3_option,
    commandline_options.pdb_option,
    commandline_options.debug_option,
    file_storage_option,
    commandline_options.loglevel_option,
    mongo_db_option,
    sql_option,
    commandline_options.capture_option,
    commandline_options.help_option,
    commandline_options.print_config_option,
    commandline_options.name_option,
    commandline_options.id_option,
    commandline_options.priority_option,
    commandline_options.unobserved_option,
    commandline_options.beat_interval_option,
    commandline_options.queue_option,
    commandline_options.force_option,
    commandline_options.comment_option,
    commandline_options.enforce_clean_option,
    tiny_db_option,
]
