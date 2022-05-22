from __future__ import annotations

import functools
import inspect
from typing import Callable, cast, Dict, Set, Tuple, Type, TypeVar

from .container import RawProvider
from .exceptions import FrozenWorldError
from .._internal import API

FREEZE_ATTR_NAME = "__antidote__freeze_sensitive"


# TODO: Inheriting GenericMeta for Python 3.6. To be removed ASAP.
@API.private
class ProviderMeta(type):
    def __new__(
        mcs: Type[ProviderMeta],
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, object],
        abstract: bool = False,
        **kwargs: object,
    ) -> ProviderMeta:
        # Every method which does not the have the does_not_freeze decorator
        # is considered
        raw_methods = {"clone", "provide", "exists", "maybe_provide", "debug", "maybe_debug"}
        attrs: Set[str] = {attr for attr in namespace.keys() if not attr.startswith("__")}
        for attr in attrs - raw_methods:
            method = namespace[attr]
            if inspect.isfunction(method) and callable(method):
                if getattr(method, FREEZE_ATTR_NAME, True):
                    namespace[attr] = _make_wrapper(attr, method)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        assert getattr(cls, "__antidote__") is None

        return cls


F = TypeVar("F", bound=Callable[..., object])


@API.private
def _make_wrapper(attr: str, method: F) -> F:
    @functools.wraps(method)
    def wrapped_method(self: RawProvider, *args: object, **kwargs: object) -> object:
        try:
            with self._bound_container_locked(freezing=True):
                # If you have a TypeError traceback pointing here you probably have
                # a mismatch between the arguments and the wrapped method signature.
                return method(self, *args, **kwargs)
        except FrozenWorldError:
            raise FrozenWorldError(
                f"Method {attr} could not be called in a frozen "
                f"world with args={args} and kwargs={kwargs}"
            )

    return cast(F, wrapped_method)
