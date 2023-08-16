import logging
import logging.handlers
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("voc4cat")
except PackageNotFoundError:  # pragma: no cover
    # package is not installed
    try:
        from ._version import version as __version__
    except ImportError:
        __version__ = "0.0.0"

# Note that nothing is passed to getLogger to set the "root" logger
logger = logging.getLogger()


def setup_logging(loglevel: int = logging.INFO, logfile: Path | None = None):
    """
    Setup logging to console and optionally a file.

    The default loglevel is INFO.
    """
    loglevel_name = os.getenv("LOGLEVEL", "").strip().upper()
    if loglevel_name in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        loglevel = getattr(logging, loglevel_name, logging.INFO)

    # Apply constraints. CRITICAL=FATAL=50 is the maximum, NOTSET=0 the minimum.
    loglevel = min(logging.FATAL, max(loglevel, logging.NOTSET))

    # Setup handler for logging to console
    logging.basicConfig(level=loglevel, format="%(levelname)-8s|%(message)s")

    if logfile is not None:
        # Setup handler for logging to file
        fh = logging.handlers.RotatingFileHandler(
            logfile, maxBytes=100000, backupCount=5
        )
        fh.setLevel(loglevel)
        fh_formatter = logging.Formatter(
            fmt="%(asctime)s|%(name)-20s|%(levelname)-8s|%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(fh_formatter)
        logger.addHandler(fh)

    # Silence noisy loggers from used packages
    logging.getLogger("PIL.PngImagePlugin").propagate = False
