Optional Features
*****************

Sacred offers a set of specialized features which are kept optional in order to
keep the list of requirements small.
This page provides a short description of these optional features.

Git Integration
===============
If the experiment sources are maintained in a git repository, then Sacred can
extract information about the current state of the repository. More
specifically it will collect the following information, which is stored by the
observers as part of the experiment info:

  * **url:** The url of the origin repository
  * **commit:** The SHA256 hash of the current commit
  * **dirty:** A boolean indicating if the repository is dirty, i.e. has
    uncommitted changes.

This can be especially useful together with the  :ref:`cmdline_enforce_clean`
(``-e / --enforce_clean``) commandline option. If this flag is used, the
experiment immediately fails with an error if started on a dirty repository.

.. note::
    Git integration can be disabled with ``save_git_info`` flag in the
    ``Experiment`` or ``Ingredient`` constructor.


Optional Observers
==================

MongoDB
-------
An observer which stores run information in a MongoDB. For more information see
:ref:`mongo_observer`.

.. note::
    Requires the `pymongo <https://api.mongodb.com/python/current>`_ package.
    Install with ``pip install pymongo``.

TinyDB
------
An observer which stores run information in a tinyDB. It can be seen as a local
alternative for the MongoDB Observer. For more information see
:ref:`tinydb_observer`.

.. note::
    Requires the
    `tinydb <http://tinydb.readthedocs.io>`_,
    `tinydb-serialization <https://github.com/msiemens/tinydb-serialization>`_,
    and `hashfs <https://github.com/dgilland/hashfs>`_ packages.
    Install with ``pip install tinydb tinydb-serialization hashfs``.

SQL
---
An observer that stores run information in a SQL database. For more information
see :ref:`sql_observer`

.. note::
    Requires the `sqlalchemy <http://www.sqlalchemy.org>`_ package.
    Install with ``pip install sqlalchemy``.

Template Rendering
------------------
The :ref:`file_observer` supports automatic report generation using the
`mako <http://www.makotemplates.org>`_ package.

.. note::
    Requires the `mako <http://www.makotemplates.org>`_ package.
    Install with ``pip install mako``.


Numpy and Pandas Integration
============================
If ``numpy`` or ``pandas`` are installed Sacred will automatically take care of
a set of type conversions and other details to make working with these packages
as smooth as possible. Normally you won't need to know about any details. But
for some cases it might be useful to know what is happening. So here is a list
of what Sacred will do:

  * automatically set the global numpy random seed (``numpy.random.seed()``).
  * if ``numpy`` is installed the :ref:`special value <special_values>` ``_rnd`` will be a
    ``numpy.random.RandomState`` instead of ``random.Random``.
  * because of these two points having numpy installed actually changes the way
    randomness is handled. Therefore ``numpy`` is then automatically added to
    the dependencies of the experiment, irrespective of its usage in the code.
  * ignore typechanges in the configuration from ``numpy`` types to normal
    types, such as ``numpy.float32`` to ``float``.
  * convert basic numpy types in the configuration to normal types if possible.
    This includes converting ``numpy.array`` to ``list``.
  * convert ``numpy.array``, ``pandas.Series``, ``pandas.DataFrame`` and
    ``pandas.Panel`` to json before storing them in the MongoDB. This includes
    instances in the :ref:`info_dict`.

YAML Format for Configurations
==============================
If the `PyYAML <http://pyyaml.org>`_ package is installed Sacred automatically
supports using config files in the yaml format (see :ref:`config_files`).

.. note::
    Requires the `PyYAML <http://pyyaml.org>`_ package.
    Install with ``pip install PyYAML``.





