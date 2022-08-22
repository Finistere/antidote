from __future__ import annotations

import inspect
from typing import Any, Callable, cast, Dict, Mapping, Optional, TYPE_CHECKING

from typing_extensions import TypeAlias, TypeGuard

from .._internal import API
from .exceptions import DoubleInjectionError
from .wiring import Methods, Wiring

if TYPE_CHECKING:
    from . import ReadOnlyCatalog

AnyF: TypeAlias = "Callable[..., Any] | staticmethod[Any] | classmethod[Any]"


@API.private
def wire_class(
    *,
    klass: type,
    wiring: Wiring,
    catalog: ReadOnlyCatalog | None,
    type_hints_locals: Optional[Mapping[str, object]],
) -> None:
    from ._objects import inject

    methods: Dict[str, AnyF] = dict()
    if isinstance(wiring.methods, Methods):
        assert wiring.methods is Methods.ALL  # Sanity check
        methods = {
            name: member
            for name, member in klass.__dict__.items()
            if _methods_all_match(member, name=name)
        }
    else:
        for method_name in wiring.methods:
            try:
                attr = klass.__dict__[method_name]
            except KeyError as e:
                raise AttributeError(method_name) from e

            if not (callable(attr) or isinstance(attr, (staticmethod, classmethod))):
                raise TypeError(
                    f"{method_name} is not callable neither a static/class method, "
                    f"but a {type(attr)!r}"
                )
            methods[method_name] = cast(AnyF, attr)

    for name, method in methods.items():
        try:
            injected_method = inject(
                method,
                fallback=wiring.fallback,
                ignore_type_hints=wiring.ignore_type_hints,
                type_hints_locals=type_hints_locals,
                app_catalog=catalog,
            )
        except DoubleInjectionError:
            if wiring.raise_on_double_injection:
                raise
            if catalog is not None:
                inject.rewire(method, app_catalog=catalog)
        else:
            if injected_method is not method:  # If something has changed
                setattr(klass, name, injected_method)


@API.private
def _methods_all_match(attr: object, *, name: str) -> TypeGuard[AnyF]:
    from .. import is_lazy
    from ..lib.interface_ext import is_interface

    # Do not inject Python dunder methods except __call__ and __init__
    if name.startswith("__") and name.endswith("__") and name != "__call__" and name != "__init__":
        return False

    # Only inject functions
    if not inspect.isfunction(attr) and not isinstance(attr, (staticmethod, classmethod)):
        return False

    # Not already wrapped
    func: Any = attr.__func__ if isinstance(attr, staticmethod) else attr
    if is_interface(func) or is_lazy(func):
        return False

    return True
