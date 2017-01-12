API Documentation
*****************
This is a construction site...

Experiment
==========

.. note::

    Experiment inherits from Ingredient_, so all methods from there also
    available in the Experiment.

.. autoclass:: sacred.Experiment
    :members:
    :inherited-members:
    :special-members: __init__

Ingredient
==========

.. autoclass:: sacred.Ingredient
    :members:
    :special-members: __init__


.. _api_run:

The Run Object
==============
The Run object can be accessed from python after the run is finished:
``run = ex.run()`` or during a run using the ``_run``
:ref:`special value <special_values>` in a
:ref:`captured function <captured_functions>`.

.. autoclass:: sacred.run.Run
    :members:
    :undoc-members:
    :special-members: __call__

ConfigScope
===========
.. autoclass:: sacred.config.config_scope.ConfigScope
    :members:
    :undoc-members:

ConfigDict
==========
.. autoclass:: sacred.config.config_dict.ConfigDict
    :members:
    :undoc-members:

Observers
=========

.. autoclass:: sacred.observers.RunObserver
    :members:
    :undoc-members:

.. autoclass:: sacred.observers.MongoObserver
    :members:
    :undoc-members:

Host Info
=========

.. automodule:: sacred.host_info
    :members:


Custom Exceptions
=================

.. autoclass:: sacred.utils.SacredInterrupt
    :members:

.. autoclass:: sacred.utils.TimeoutInterrupt
    :members:
