Configuration Injection
***********************
Once you've set up your configuration, the next step is to use those values in
the code of the experiment. To make this as easy as possible Sacred
automatically fills in the missing parameters of a *captured function* with
configuration values. So for example this would work:

.. code-block:: python

    ex = Experiment('captured_func_demo')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.automain
    def my_main(a, b):
        print("a =", a)  # 10
        print("b =", b)  # test


Captured Functions
==================
Sacred automatically injects configuration values for captured functions.
Apart from the main function (marked by ``@ex.main`` or ``@ex.automain``) this
includes all functions marked with ``@ex.capture``. So the following example
works as before:

.. code-block:: python

    ex = Experiment('captured_func_demo2')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.capture
    def print_a_and_b(a, b):
        print("a =", a)
        print("b =", b)

    @ex.automain
    def my_main():
        print_a_and_b()

Notice that we did not pass any arguments to ``print_a_and_b`` in ``my_main``.
These are filled in from the configuration. We can however override these values
in any way we like:

.. code-block:: python

    @ex.automain
    def my_main():
        print_a_and_b()          # prints '10' and 'test'
        print_a_and_b(3)         # prints '3'  and 'test'
        print_a_and_b(3, 'foo')  # prints '3'  and 'foo'
        print_a_and_b(b='foo')   # prints '10' and 'foo'


.. note::
    All functions decorated with ``@ex.main``, ``@ex.automain``, and
    ``@ex.command`` are also captured functions.


In case of multiple values for the same parameter the priority is:
  1. explicitly passed arguments (both positional and keyword)
  2. configuration values
  3. default values

You will still get an appropriate error in the following cases:
    - missing value that is not found in configuration
    - unexpected keyword arguments
    - too many positional arguments

.. note::
    Be careful with naming your parameters, because configuration injection can
    hide some missing value errors from you, by (unintentionally) filling them
    in from the configuration.

Special Values
==============
There are a couple of special parameters that captured functions can accept.
These might change, and are not well documented yet, so be careful:

  - ``_seed`` : a seed that is different for every invocation (-> Controlling Randomness)
  - ``_rnd`` : a random state seeded with ``seed``
  - ``_log`` : a logger for that function
  - ``_run`` : the run object for the current run