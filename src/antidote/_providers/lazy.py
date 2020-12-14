from typing import Any, Callable, cast, Hashable

from .._compatibility.typing import final
from .._internal import API
from .._internal.utils import debug_repr, FinalImmutable
from ..core import Container, DependencyInstance, StatelessProvider
from ..core.utils import DependencyDebug


@API.private
class Lazy:
    def debug_info(self) -> DependencyDebug:
        raise NotImplementedError()  # pragma: no cover

    def lazy_get(self, container: Container) -> DependencyInstance:
        raise NotImplementedError()  # pragma: no cover


@API.private
@final
class FastLazyConst(FinalImmutable, Lazy):
    __slots__ = ('name', 'dependency', 'method_name', 'value', 'cast')
    name: str
    dependency: Hashable
    method_name: str
    value: object
    cast: Callable[[Any], Any]

    def __init__(self, name: str, dependency: Hashable, method_name: str, value: object,
                 cast: Callable[[Any], Any]) -> None:
        super().__init__(
            name=name,
            dependency=dependency,
            method_name=method_name,
            value=value,
            cast=cast
        )

    def debug_info(self) -> DependencyDebug:
        from ..lazy import LazyCall
        if isinstance(self.dependency, LazyCall):
            cls: type = cast(type, self.dependency.func)
        else:
            cls = cast(type, self.dependency)
        return DependencyDebug(f"Const: {debug_repr(cls)}.{self.name}",
                               singleton=True,
                               dependencies=[self.dependency],
                               # TODO: Would be great if the first argument of the method
                               #       didn't show as unknown as it's always provided.
                               wired=[getattr(cls, self.method_name)])

    def lazy_get(self, container: Container) -> DependencyInstance:
        # TODO: Waiting for a fix: https://github.com/python/mypy/issues/6910
        _cast = cast(Callable[[Any], Any], getattr(self, 'cast'))
        return DependencyInstance(
            _cast(getattr(container.get(self.dependency),
                          self.method_name)(self.value)),
            singleton=True
        )


@API.private
@final
class LazyProvider(StatelessProvider[Lazy]):
    def exists(self, dependency: Hashable) -> bool:
        return isinstance(dependency, Lazy)

    def debug(self, dependency: Lazy) -> DependencyDebug:
        return dependency.debug_info()

    def provide(self, dependency: Lazy, container: Container
                ) -> DependencyInstance:
        return dependency.lazy_get(container)
