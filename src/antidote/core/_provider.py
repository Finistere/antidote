import functools
import inspect
from typing import Set

from .container import RawDependencyProvider
from .exceptions import FrozenContainerError, FrozenWorldError
from .._internal import API

_FREEZE_ATTR_NAME = "__antidote__freeze_sensitive"


@API.private
class ProviderMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        # Every method which does not the have the does_not_freeze decorator
        # is considered
        raw_method = {"clone", "provide"}
        attrs: Set[str] = {attr for attr in namespace.keys() if
                           not attr.startswith("__")}
        for attr in (attrs - raw_method):
            method = namespace[attr]
            if not inspect.isfunction(method):
                continue

            if getattr(method, _FREEZE_ATTR_NAME, True):
                namespace[attr] = _make_wrapper(attr, method)

        cls = super().__new__(mcls, name, bases, namespace)
        assert getattr(cls, "__antidote__") is None

        return cls


@API.private
def _make_wrapper(attr, method):
    @functools.wraps(method)
    def wrapped_method(self: RawDependencyProvider, *args, **kwargs):
        try:
            with self._ensure_not_frozen():
                return method(self, *args, **kwargs)
        except FrozenContainerError:
            raise FrozenWorldError(
                f"Method {attr} could not be called in a frozen "
                f"world with args={args} and kwargs={kwargs}"
            )

    return wrapped_method
