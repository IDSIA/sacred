.. _settings:

Settings
********

Some of Sacred's general behaviour is configurable via ``sacred.SETTINGS``.
Its entries can be set simply by importing and modifying it using dict or attribute notation:

.. code-block:: python

    from sacred import SETTINGS
    SETTINGS['HOST_INFO']['INCLUDE_GPU_INFO'] = False
    SETTINGS.HOST_INFO.INCLUDE_GPU_INFO = False  # equivalent

Settings
========
Here is a brief list of all currently available options.


* ``CAPTURE_MODE`` *(default: 'fd' (linux/osx) or 'sys' (windows))*
  configure how stdout/stderr are captured. ['no', 'sys', 'fd']

* ``CONFIG``

  * ``ENFORCE_KEYS_MONGO_COMPATIBLE`` *(default: True)*
    make sure all config keys are compatible with MongoDB
  * ``ENFORCE_KEYS_JSONPICKLE_COMPATIBLE`` *(default: True)*
    make sure all config keys are serializable with jsonpickle
  * ``ENFORCE_KEYS_JSONPICKLE_COMPATIBLE`` *(default: True)*
    THIS IS IMPORTANT. Only deactivate if you know what you're doing.
  * ``ENFORCE_VALID_PYTHON_IDENTIFIER_KEYS`` *(default: False)*
    make sure all config keys are valid python identifiers
  * ``ENFORCE_STRING_KEYS`` *(default: False)*
    make sure all config keys are strings
  * ``ENFORCE_KEYS_NO_EQUALS`` *(default: True)*
    make sure no config key contains an equals sign
  * ``IGNORED_COMMENTS`` *(default: ['^pylint:', '^noinspection'])*
    list of regex patterns to filter out certain IDE or linter directives
    from in-line comments in the documentation.
  * ``READ_ONLY_CONFIG`` *(default: True)*
    Make the configuration read-only inside of captured functions. This
    only works to a limited extend because custom types cannot be
    controlled.

* ``HOST_INFO``

  * ``INCLUDE_GPU_INFO`` *(default: True)*
    Try to collect information about GPUs using the nvidia-smi tool.
    Deactivating this can cut the start-up time of a Sacred run by about 1 sec.
  * ``CAPTURED_ENV`` *(default: [])*
    List of ENVIRONMENT variable names to store in the host-info.


* ``COMMAND_LINE``

  * ``STRICT_PARSING`` *(default: False)*
    disallow string fallback, if parsing a value from command-line failed.
    This enforces the usage of quotes in the command-line. Note that this can
    be very tedious since bash removes one set of quotes, such that double
    quotes will be needed.

