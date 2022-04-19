from .constant import (Const, Constant, ConstantFactory, ConstantValueProviderFunction,
                       TypedConstantFactory, ConstantValueProvider)
from .lazy import lazy, LazyWrappedFunction

from ..._internal import API

__all__ = ['ConstantFactory', 'TypedConstantFactory', 'ConstantValueProviderFunction',
           'ConstantValueProvider', 'const', 'lazy', 'LazyWrappedFunction',
           'register_lazy_provider', 'Constant']


@API.private
def __const() -> Const:
    from ._constant_factory import ConstImpl
    return ConstImpl()


# Singleton instance of Const.
const: Const = __const()


@API.experimental
def register_lazy_provider() -> None:
    from ... import world
    from ._provider import LazyProvider
    world.provider(LazyProvider)
