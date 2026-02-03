from __future__ import annotations


class TeleCLIException(Exception):
    """Base exception class for Tele CLI."""

    pass


class ConfigError(TeleCLIException, ValueError):
    """Exception raised when there is an error in the configuration file."""

    pass
