import functools
import inspect
from typing import Set

from .container import RawProvider
from .exceptions import FrozenWorldError
from .._compatibility.typing import GenericMeta
from .._internal import API

_FREEZE_ATTR_NAME = "__antidote__freeze_sensitive"


# TODO: Inheriting GenericMeta for Python 3.6. To be removed ASAP.
@API.private
class ProviderMeta(GenericMeta):
    def __new__(mcls, name, bases, namespace, abstract=False, **kwargs):
        # Every method which does not the have the does_not_freeze decorator
        # is considered
        raw_methods = {"clone", "provide", "exists", "maybe_provide", "debug",
                       "maybe_debug"}
        attrs: Set[str] = {attr for attr in namespace.keys() if
                           not attr.startswith("__")}
        for attr in (attrs - raw_methods):
            method = namespace[attr]
            if not inspect.isfunction(method):
                continue

            if getattr(method, _FREEZE_ATTR_NAME, True):
                namespace[attr] = _make_wrapper(attr, method)

        cls = super().__new__(mcls, name, bases, namespace, **kwargs)  # type: ignore
        assert getattr(cls, "__antidote__") is None

        return cls


@API.private
def _make_wrapper(attr, method):
    @functools.wraps(method)
    def wrapped_method(self: RawProvider, *args, **kwargs):
        try:
            with self._ensure_not_frozen():
                return method(self, *args, **kwargs)
        except FrozenWorldError:
            raise FrozenWorldError(
                f"Method {attr} could not be called in a frozen "
                f"world with args={args} and kwargs={kwargs}"
            )

    return wrapped_method
