import inspect
import sys

colored_exception_output = True

if colored_exception_output:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    GREY = '\033[90m'
    ENDC = '\033[0m'
else:
    BLUE = ''
    GREEN = ''
    RED = ''
    GREY = ''
    ENDC = ''

CONFLICTING = RED


from sacred.utils import get_by_dotted_path, iterate_flattened

if sys.version_info[0] == 2:
    import errno


    class FileNotFoundError(IOError):
        def __init__(self, msg):
            super(FileNotFoundError, self).__init__(errno.ENOENT, msg)
else:
    # Reassign so that we can import it from here
    FileNotFoundError = FileNotFoundError


class ObserverError(Exception):
    """Error that an observer raises but that should not make the run fail."""


class SacredInterrupt(Exception):
    """Base-Class for all custom interrupts.

    For more information see :ref:`custom_interrupts`.
    """

    STATUS = "INTERRUPTED"


class TimeoutInterrupt(SacredInterrupt):
    """Signal a that the experiment timed out.

    This exception can be used in client code to indicate that the run
    exceeded its time limit and has been interrupted because of that.
    The status of the interrupted run will then be set to ``TIMEOUT``.

    For more information see :ref:`custom_interrupts`.
    """

    STATUS = "TIMEOUT"


class SacredError(Exception):
    def __init__(self, *args: object, print_traceback=True,
                 filter_traceback=None, print_usage=False) -> None:
        super().__init__(*args)
        self.print_traceback = print_traceback
        self.filter_traceback = filter_traceback
        self.print_usage = print_usage


class CircularDependencyError(SacredError):
    """The ingredients of the current experiment form a circular dependency."""

    def __init__(self, *args: object, ingredients=None) -> None:
        super().__init__(*args)
        if ingredients is None:
            ingredients = []
        self.__ingredients__ = ingredients
        self.__circular_depencency_handled__ = False

    def __str__(self):
        return '->'.join([i.path for i in reversed(self.__ingredients__)])


class ConfigError(SacredError):
    def __init__(self, *args, conflicting_configs=(), print_traceback=True,
                 filter_traceback=True,
                 print_config_sources=True,
                 print_usage=False) -> None:
        super().__init__(*args, print_traceback=print_traceback,
                         filter_traceback=filter_traceback,
                         print_usage=print_usage)
        self.print_config_sources = print_config_sources

        if isinstance(conflicting_configs, str):
            conflicting_configs = (conflicting_configs,)

        self.conflicting_configs = conflicting_configs
        self.__prefix_handled__ = False
        self.__config_sources__ = ()
        self.__config__ = {}

    def __str__(self):
        s = super().__str__()
        if self.print_config_sources:
            s += '\nConflicting configuration values:'
            for conflicting_config in self.conflicting_configs:
                s += '\n  {}{}={}{}'.format(RED, conflicting_config,
                                       self.__config__[
                                           conflicting_config], ENDC)
                s += '\n    defined in {}'.format(
                        get_by_dotted_path(
                            self.__config_sources__,
                            conflicting_config
                        ).get_source_string_for_config(
                            conflicting_config
                        )
                    )
        return s


class InvalidConfigError(ConfigError):
    pass


class MissingConfigError(SacredError):
    def __init__(self, *args, missing_configs=(), function=None,
                 print_traceback=True, filter_traceback=True,
                 print_usage=True):
        self.func = function
        self.missing_configs = missing_configs
        super().__init__(
            *args,
            self.missing_configs,
            print_traceback=print_traceback,
            filter_traceback=filter_traceback,
            print_usage=print_usage
        )

    def __str__(self):
        s = str(self.args)
        if self.func.ingredient is not None:
            func_file = inspect.getfile(self.func)
            _, offset = inspect.getsourcelines(self.func)

            captured_func_source = '"{}:{}"'.format(func_file, offset)

            # we can't import Experiment here for `isinstance`, but check
            # for attribute 'run' should do
            if hasattr(self.func.ingredient, 'run'):
                s += '\nFunction that caused the exception: {} captured by ' \
                     'the experiment "{}" at {}'.format(
                    self.func,
                    self.func.ingredient.path,
                    captured_func_source,
                )
            else:
                s += '\nFunction that caused the exception: {} captured by ' \
                     'the ingredient "{}" at {}'.format(
                    self.func,
                    self.func.ingredient.path,
                    captured_func_source)
        else:
            s += '\nFunction that caused the exception: {}'.format(self.func)
        return s


class NamedConfigNotFoundError(SacredError):
    def __init__(self, *args, named_config, print_traceback=False,
                 filter_traceback=None, print_usage=False):
        super().__init__(
            *args,
            print_traceback=print_traceback,
            filter_traceback=filter_traceback,
            print_usage=print_usage
        )
        self.named_config = named_config


class ConfigAddedError(ConfigError):
    SPECIAL_ARGS = {'_log', '_config', '_seed', '__doc__', 'config_filename', '_run'}

    def __init__(self, *args, conflicting_configs=(), print_traceback=False,
                 filter_traceback=True, print_config_sources=True,
                 print_usage=False, print_suggestions=True,
                 captured_args=()) -> None:
        args = ('Added new config entry "{}{}{}" that is not used anywhere'.format(CONFLICTING, conflicting_configs[0], ENDC),)
        super().__init__(*args, conflicting_configs=conflicting_configs,
                         print_traceback=print_traceback,
                         filter_traceback=filter_traceback,
                         print_config_sources=print_config_sources,
                         print_usage=print_usage,
                         )
        self.print_suggestions = print_suggestions
        self.captured_args = captured_args

    def __str__(self):
        s = super().__str__()
        if self.print_suggestions:
            possible_keys = self.captured_args - self.SPECIAL_ARGS

            for c in self.conflicting_configs:
                # TODO: get suggestion
                suggestion = possible_keys.pop()
                s += '\nDid you mean "{}" instead of "{}"?'.format(suggestion, c)
        return s




