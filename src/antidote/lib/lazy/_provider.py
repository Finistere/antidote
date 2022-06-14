from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast, Dict, Generic, Tuple, TypeVar

from typing_extensions import final, TypeGuard

from ..._internal import API, debug_repr_call
from ..._internal.utils import CachedMeta
from ...core import (
    CatalogId,
    DependencyDebug,
    LifeTime,
    ProvidedDependency,
    Provider,
    ReadOnlyCatalog,
)
from ...core.data import Dependency, TestEnvKind

T = TypeVar("T")

__all__ = ["LazyDependency", "lazy_call", "LazyProvider"]


@API.private
class LazyDependency:
    catalog_id: CatalogId

    def __antidote_debug__(self) -> DependencyDebug:
        raise NotImplementedError()  # pragma: no cover

    def __antidote_unsafe_provide__(
        self, catalog: ReadOnlyCatalog, out: ProvidedDependency
    ) -> None:
        raise NotImplementedError()  # pragma: no cover


@API.private
def lazy_call(
    *,
    func: Callable[..., T],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
    lifetime: LifeTime,
    catalog_id: CatalogId,
) -> Dependency[T]:
    return LazyCallImpl(
        func=func, args=args, kwargs=kwargs, lifetime=lifetime, catalog_id=catalog_id
    )


@API.private
@final
@dataclass(frozen=True)
class LazyCallImpl(LazyDependency, Generic[T], metaclass=CachedMeta):
    __slots__ = ("catalog_id", "__func", "__args", "__kwargs", "__lifetime")
    catalog_id: CatalogId
    __lifetime: LifeTime
    __func: Callable[..., T]
    __args: Tuple[Any, ...]
    __kwargs: Dict[str, Any]
    __hash: int

    def __init__(
        self,
        *,
        func: Callable[..., T],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        lifetime: LifeTime,
        catalog_id: CatalogId,
    ) -> None:
        try:
            _hash = hash((catalog_id.name, lifetime, func, args, tuple(sorted(kwargs.items()))))
        except TypeError:
            if lifetime is not LifeTime.TRANSIENT:
                raise
            _hash = object.__hash__(self)
        object.__setattr__(self, "catalog_id", catalog_id)
        object.__setattr__(self, f"_{type(self).__name__}__lifetime", lifetime)
        object.__setattr__(self, f"_{type(self).__name__}__func", func)
        object.__setattr__(self, f"_{type(self).__name__}__args", args)
        object.__setattr__(self, f"_{type(self).__name__}__kwargs", kwargs)
        object.__setattr__(self, f"_{type(self).__name__}__hash", _hash)

    def __repr__(self) -> str:
        return (
            f"LazyCall(catalog_id={self.catalog_id}, lifetime={self.__lifetime.name}, "
            f"func={self.__func!r}, args={self.__args!r}, kwargs={self.__kwargs!r})"
        )

    def __antidote_debug_repr__(self) -> str:
        return f"<lazy> {debug_repr_call(self.__func, self.__args, self.__kwargs)}"

    def __antidote_debug__(self) -> DependencyDebug:
        return DependencyDebug(
            description=self.__antidote_debug_repr__(),
            lifetime=self.__lifetime,
            wired=self.__func,
        )

    def __antidote_unsafe_provide__(
        self, catalog: ReadOnlyCatalog, out: ProvidedDependency
    ) -> None:
        if self.__lifetime is LifeTime.SCOPED:
            func = self.__func
            args = self.__args
            kwargs = self.__kwargs

            def callback() -> T:
                return func(*args, **kwargs)

        else:
            callback = None  # type: ignore

        out.set_value(
            self.__func(*self.__args, **self.__kwargs),
            lifetime=self.__lifetime,
            callback=callback,
        )

    def __hash__(self) -> int:
        return self.__hash

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LazyCallImpl)
            and other.__func is self.__func
            and other.__lifetime is self.__lifetime
            and other.catalog_id.name is self.catalog_id.name
            and other.__args == self.__args
            and other.__kwargs == self.__kwargs
        )

    def __antidote_dependency_hint__(self) -> T:
        return cast(T, self)


@API.private
@final
@dataclass(frozen=True, init=False, eq=False)
class LazyProvider(Provider):
    __slots__ = ()

    def can_provide(self, dependency: object) -> TypeGuard[LazyDependency]:  # pyright: ignore
        # TODO: take into account test_env kind...
        return (
            isinstance(dependency, LazyDependency)
            and self._catalog.id.name is dependency.catalog_id.name
            and not any(
                te.kind is TestEnvKind.NEW or te.kind is TestEnvKind.EMPTY
                for te in self._catalog.id.test_env[
                    len(dependency.catalog_id.test_env) :  # noqa E203
                ]
            )
        )

    def maybe_debug(self, dependency: object) -> DependencyDebug | None:
        return dependency.__antidote_debug__() if self.can_provide(dependency) else None

    def unsafe_maybe_provide(self, dependency: object, out: ProvidedDependency) -> None:
        if self.can_provide(dependency):
            dependency.__antidote_unsafe_provide__(self._catalog, out)
