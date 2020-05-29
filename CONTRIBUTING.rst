============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/IDSIA/sacred/issues.

If you are reporting a bug, please include:

* Any details about your local setup that might be helpful in troubleshooting.
* Steps to reproduce the bug, and if possible a minimal example demonstrating the problem.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to fix it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Sacred could always use more documentation, whether as part of the
official Sacred docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/IDSIA/sacred/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `sacred` for
local development.

1. Fork_ the `sacred` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/sacred.git

3. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

4. Create your development environment and install the pre-commit hooks
    $ # Activate your environment
    $ pip install -r dev-requirements.txt
    $ pre-commit install

Now you can make your changes locally.

5. When you're done making changes, check that your changes pass style and unit
   tests, including testing other Python versions with tox::

    $ tox

To get tox, just pip install it.

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

.. _Fork: https://github.com/IDSIA/sacred/fork

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. Pull requests should be made on their own branch or against master.
1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for all Python versions listed in the ``setup.py``.
   Check https://travis-ci.org/IDSIA/sacred/pull_requests
   for active pull requests or run the ``tox`` command and make sure that the tests pass for all supported Python versions.
