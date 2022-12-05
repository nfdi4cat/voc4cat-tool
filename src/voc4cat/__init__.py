# -*- coding: utf-8 -*-
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("voc4cat")
except PackageNotFoundError:
    # package is not installed
    try:
        from ._version import version as __version__
    except ImportError:
        __version__ = "0.0.0"
