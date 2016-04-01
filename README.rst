Sacred
======

    | *Every experiment is sacred*
    | *Every experiment is great*
    | *If an experiment is wasted*
    | *God gets quite irate*

|pypi| |py_versions| |license| |doi|

|unix_build| |windows_build| |coverage| |code_quality| |codacy|

Sacred is a tool to help you configure, organize, log and reproduce experiments.
It is designed to do all the tedious overhead work that you need to do around
your actual experiment in order to:

- keep track of all the parameters of your experiment
- easily run your experiment for different settings
- save configurations for individual runs in a database
- reproduce your results

Sacred achieves this through the following main mechanisms:

-  **ConfigScopes** A very convenient way of the local variables in a function
   to define the parameters your experiment uses.
-  **Config Injection**: You can access all parameters of your configuration
   from every function. They are automatically injected by name.
-  **Command-line interface**: You get a powerful command-line interface for each
   experiment that you can use to change parameters and run different variants.
-  **Observers**: Sacred provides Observers that log all kinds of information
   about your experiment, its dependencies, the configuration you used,
   the machine it is run on, and of course the result. These can be saved
   to a MongoDB, for easy access later.
-  **Automatic seeding** helps controlling the randomness in your experiments,
   such that the results remain reproducible.

*Note: In order to ensure the reproducibility of your experiments, sacred cannot be launched from ipython notebooks (see https://github.com/IDSIA/sacred/issues/100)*


Example
-------
+------------------------------------------------+--------------------------------------------+
| **Script to train an SVM on the iris dataset** | **The same script as a Sacred experiment** |
+------------------------------------------------+--------------------------------------------+
| .. code:: python                               | .. code:: python                           |
|                                                |                                            |
|  from numpy.random import permutation          |   from numpy.random import permutation     |
|  from sklearn import svm, datasets             |   from sklearn import svm, datasets        |
|                                                |   from sacred import Experiment            |
|                                                |   ex = Experiment('iris_rbf_svm')          |
|                                                |                                            |
|                                                |   @ex.config                               |
|                                                |   def cfg():                               |
|  C = 1.0                                       |     C = 1.0                                |
|  gamma = 0.7                                   |     gamma = 0.7                            |
|                                                |                                            |
|                                                |   @ex.automain                             |
|                                                |   def run(C, gamma):                       |
|  iris = datasets.load_iris()                   |     iris = datasets.load_iris()            |
|  perm = permutation(iris.target.size)          |     per = permutation(iris.target.size)    |
|  iris.data = iris.data[perm]                   |     iris.data = iris.data[per]             |
|  iris.target = iris.target[perm]               |     iris.target = iris.target[per]         |
|  clf = svm.SVC(C, 'rbf', gamma=gamma)          |     clf = svm.SVC(C, 'rbf', gamma=gamma)   |
|  clf.fit(iris.data[:90],                       |     clf.fit(iris.data[:90],                |
|          iris.target[:90])                     |             iris.target[:90])              |
|  print(clf.score(iris.data[90:],               |     return clf.score(iris.data[90:],       |
|                  iris.target[90:]))            |                      iris.target[90:])     |
+------------------------------------------------+--------------------------------------------+

Documentation
-------------
The documentation is hosted at `ReadTheDocs <http://sacred.readthedocs.org/>`_.

Installing
----------
You can directly install it from the Python Package Index with pip:

    pip install sacred

Or if you want to do it manually you can checkout the current version from git
and install it yourself:

   | git clone https://github.com/IDSIA/sacred.git
   | cd sacred
   | python setup.py install

You might want to also install the ``numpy`` and the ``pymongo`` packages. They are
optional dependencies but they offer some cool features:

    pip install numpy, pymongo

Tests
-----
The tests for sacred use the `py.test <http://pytest.org/latest/>`_ package.
You can execute them by running ``py.test`` in the sacred directory like this:

    py.test

There is also a config file for `tox <https://testrun.org/tox/latest/>`_ so you
can automatically run the tests for various python versions like this:

    tox


License
-------
This project is released under the terms of the `MIT license <http://opensource.org/licenses/MIT>`_.

.. |pypi| image:: https://img.shields.io/pypi/v/sacred.svg
    :target: https://pypi.python.org/pypi/sacred
    :alt: Current PyPi Version

.. |py_versions| image:: https://img.shields.io/pypi/pyversions/sacred.svg
    :target: https://pypi.python.org/pypi/sacred
    :alt: Supported Python Versions

.. |license| image:: https://img.shields.io/badge/license-MIT-blue.png
    :target: http://choosealicense.com/licenses/mit/
    :alt: MIT licensed

.. |rtfd| image:: https://readthedocs.org/projects/sacred/badge/?version=latest&style=flat
    :target: http://sacred.readthedocs.org/
    :alt: ReadTheDocs

.. |doi| image:: https://zenodo.org/badge/doi/10.5281/zenodo.16386.svg
    :target: http://dx.doi.org/10.5281/zenodo.16386
    :alt: DOI for this release

.. |unix_build| image:: https://img.shields.io/travis/IDSIA/sacred.svg?branch=master&style=flat&label=unix%20build
    :target: https://travis-ci.org/IDSIA/sacred
    :alt: Travis-CI Status

.. |windows_build| image:: https://img.shields.io/appveyor/ci/qwlouse/sacred.svg?style=flat&label=windows%20build
    :target: https://ci.appveyor.com/project/Qwlouse/sacred
    :alt: appveyor-CI Status

.. |coverage| image:: https://coveralls.io/repos/IDSIA/sacred/badge.svg
    :target: https://coveralls.io/r/IDSIA/sacred
    :alt: Coverage Report

.. |code_quality| image:: https://scrutinizer-ci.com/g/IDSIA/sacred/badges/quality-score.png?b=master
    :target: https://scrutinizer-ci.com/g/IDSIA/sacred/
    :alt: Code Scrutinizer Quality

.. |codacy| image:: https://img.shields.io/codacy/acb7bba4467e47deaf260d6df5c0279f.svg?style=flat
    :target: https://www.codacy.com/app/qwlouse/sacred
    :alt: Codacity rating


