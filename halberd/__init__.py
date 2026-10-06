"""Halberd BAS - Open-source Breach and Attack Simulation."""

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("halberd-bas")
except Exception:  # not installed (running from source tree)
    __version__ = "0.3.1"
