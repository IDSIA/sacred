"""Contains meta-information about the Sacred package.

It is kept simple and separate from the main module, because this information
is also read by the setup.py. And during installation the sacred module cannot
yet be imported.
"""

__all__ = ("__version__", "__author__", "__author_email__", "__url__")

__version__ = "0.8.7"

__author__ = "Klaus Greff"
__author_email__ = "klaus.greff@startmail.com"

__url__ = "https://github.com/IDSIA/sacred"
