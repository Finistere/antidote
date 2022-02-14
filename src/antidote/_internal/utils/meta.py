# pyright: reportUnknownMemberType=false
from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional, Tuple, Type

from .. import API

_ABSTRACT_FLAG = '__antidote_abstract'


@API.private
class FinalMeta(type):
    def __new__(mcs: Type[FinalMeta],
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object]
                ) -> FinalMeta:
        for b in bases:
            if isinstance(b, FinalMeta):
                raise TypeError(f"Type '{b.__name__}' cannot be inherited.")

        return super().__new__(mcs, name, bases, namespace)


@API.private
class AbstractMeta(type):
    def __new__(mcs: Type[AbstractMeta],
                name: str,
                bases: Tuple[type, ...],
                namespace: Dict[str, object],
                abstract: bool = False
                ) -> AbstractMeta:
        namespace[_ABSTRACT_FLAG] = abstract
        if not abstract:
            for b in bases:
                if isinstance(b, mcs) and not getattr(b, _ABSTRACT_FLAG):
                    raise TypeError(
                        f"Cannot inherit a service which is not defined abstract. "
                        f"Consider defining {b} abstract by adding 'abstract=True' as a "
                        f"metaclass parameter. If so, Antidote won't use it.")

        return super().__new__(mcs, name, bases, namespace)


@API.private
class Singleton(metaclass=AbstractMeta, abstract=True):
    __instance: ClassVar[Optional[Any]] = None

    def __new__(cls) -> Any:
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance
