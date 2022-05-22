# pyright: reportUnusedFunction=warning
from __future__ import annotations

from typing import Any, cast, Dict, FrozenSet, Tuple, Type, TypeVar

from ._internal import API
from ._internal.utils import AbstractMeta
from .lib.lazy import const
from .lib.lazy._constant import ConstantImpl

T = TypeVar("T")


@API.private
class ConstantsMeta(AbstractMeta):
    def __new__(
        mcs: Type[ConstantsMeta],
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, object],
        **kwargs: Any,
    ) -> ConstantsMeta:
        cls = cast(ConstantsMeta, super().__new__(mcs, name, bases, namespace, **kwargs))
        if not kwargs.get("abstract"):
            _configure_constants(cls)
        return cls


@API.private
def _configure_constants(cls: type, conf: object = None) -> None:
    from .constants import Constants
    from .service import service

    conf = conf or getattr(cls, "__antidote__", None)
    if not isinstance(conf, Constants.Conf):
        raise TypeError(
            f"Constants configuration (__antidote__) is expected to be a "
            f"{Constants.Conf}, not a {type(conf)}"
        )

    cls = service(cls, singleton=True, wiring=conf.wiring)
    auto_cast_types: FrozenSet[type] = conf.auto_cast
    provide_const = getattr(cls, Constants.provide_const.__name__)

    # Ensure the wrapper is properly detected as a method by @const.provider
    provider = const.provider(provide_const)

    @provider.converter
    def auto_converter(value: object, tpe: Type[T]) -> T:
        if tpe in auto_cast_types:
            # for Mypy
            return tpe(value)  # type: ignore
        return cast(T, value)

    for name, attr in list(cls.__dict__.items()):
        if isinstance(attr, ConstantImpl):
            attr = cast(ConstantImpl[object, object, object], attr)
            cst = cast(
                ConstantImpl[object, object, object],
                provider.const[attr.type_](attr.arg, default=attr.default),
            )
            cst.__set_name__(cls, name)
            setattr(cls, name, cst)
