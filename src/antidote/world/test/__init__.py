"""
Testing utilities with Antidote. Also used by Antidote itself.
"""
from . import override
from ._methods import clone, empty, factory, maybe_provide_from, new, singleton

__all__ = ['clone', 'empty', 'factory', 'maybe_provide_from', 'new', 'singleton']
