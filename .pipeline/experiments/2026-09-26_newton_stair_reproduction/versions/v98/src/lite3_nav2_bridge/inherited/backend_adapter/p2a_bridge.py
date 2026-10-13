"""Installed-package import of the unchanged P2A data/adapter definitions.

The legacy runtime found core.py through repository-relative parents. In this
Foxy package all three Python modules are installed together. No legacy mission
runtime is instantiated by the Nav2 gateway.
"""
from navigation_service import core


def load_p2a_core():
    return core
