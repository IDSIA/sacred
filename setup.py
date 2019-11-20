from pathlib import Path

from setuptools import setup
import os

classifiers = """
Development Status :: 5 - Production/Stable
Intended Audience :: Science/Research
Natural Language :: English
Operating System :: OS Independent
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Topic :: Utilities
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Artificial Intelligence
Topic :: Software Development :: Libraries :: Python Modules
License :: OSI Approved :: MIT License
"""

try:
    from sacred import __about__

    about = __about__.__dict__
except ImportError:
    # installing - dependencies are not there yet
    # Manually extract the __about__
    about = dict()
    exec(open("sacred/__about__.py").read(), about)


setup(
    name="sacred",
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    packages=["sacred", "sacred.observers", "sacred.config", "sacred.stflow"],
    package_data={"sacred": [os.path.join("data", "*")]},
    scripts=[],
    install_requires=Path("requirements.txt").read_text().splitlines(),
    tests_require=["mock>=0.8, <3.0", "pytest==4.3.0"],
    classifiers=list(filter(None, classifiers.split("\n"))),
    description="Facilitates automated and reproducible experimental research",
    long_description=Path("README.rst").read_text(encoding="utf-8"),
)
