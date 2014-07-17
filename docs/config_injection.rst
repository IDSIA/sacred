Configuration Injection
***********************
Once you've set up your configuration, the next step is to use those values in
the code of the experiment. In order to get the values there ``sacred`` uses a
method called *dependency injection* for configuration values. This means that
it will automatically fill in the missing parameters of all
*captured functions* with configuration values:

.. code-block:: python

    ex = Experiment('captured_func_demo')

    @ex.config
    def my_config1():
        a = 10
        b = 'test'

    @ex.automain
    def my_main(a, b):
        print("a =", a)
        print("b =", b)


Captured Functions
==================

  - explain ``@ex.capture``
  - ``@ex.main``, ``@ex.automain``, and ``@ex.command`` are also captured functions

Priority
========

  1. explicitly passed arguments (both positional and keyword)
  2. configuration values
  3. default values

You still get errors for

  - missing values
  - unexpected keyword arguments
  - too many positional arguments

Special Values
==============
These might change, and are not well documented yet:

  - ``seed`` : a seed that is different for every invocation (-> Controlling Randomness)
  - ``rnd`` : a random state seeded with ``seed``
  - ``log`` : a logger for that function
  - ``run`` : the run object for the current run