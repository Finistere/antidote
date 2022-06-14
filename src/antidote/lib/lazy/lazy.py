from __future__ import annotations

from typing import Any, Callable, overload, TypeVar

from typing_extensions import Concatenate, ParamSpec, Protocol

from ..._internal import API, Default
from ...core import Catalog, Dependency, LifetimeType, TypeHintsLocals, world

__all__ = ["is_lazy", "Lazy", "LazyMethod", "LazyFunction"]

P = ParamSpec("P")
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])
Out = TypeVar("Out", covariant=True)


@API.public
class LazyFunction(Protocol[P, Out]):
    @property
    def __wrapped__(self) -> Callable[P, Out]:
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...


@API.public
class LazyMethod(Protocol[P, Out]):
    # Have to copy-paste LazyFunction for Mypy... error: ParamSpec "P" is unbound
    @property
    def __wrapped__(self) -> Callable[Concatenate[Any, P], Out]:
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...

    def __get__(self, instance: object, owner: type) -> LazyMethod[P, Out]:
        ...


@API.public
class LazyProperty(Dependency[Out], Protocol[Out]):
    @property
    def __wrapped__(self) -> Callable[[Any], Out]:
        ...


@API.public
class LazyValue(Dependency[Out], Protocol[Out]):
    @property
    def __wrapped__(self) -> Callable[[], Out]:
        ...


@API.public
class Lazy(Protocol):
    @overload
    def __call__(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> DecoratorLazyFunction:
        ...

    @overload
    def __call__(
        self,
        __func: staticmethod[Callable[P, T]],
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(
        self,
        __func: Callable[P, T],
        *,
        lifetime: LifetimeType = ...,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyFunction[P, T]:
        ...

    def __call__(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        """
        As the name implies, a lazy function executes lazily. The new function now returns a dependency
        which will only be executed when retrieving it through a catalog such as :py:obj:`.world` or
        at injection.

        .. doctest:: lib_lazy_lazy

            >>> from dataclasses import dataclass
            >>> from antidote import inject, lazy, world
            >>> @dataclass
            ... class Template:
            ...     name: str
            >>> @lazy
            ... def main_template() -> Template:
            ...     print("# Called main_template()")
            ...     return Template("main")
            >>> @inject
            ... def f(t: Template = inject[main_template()]) -> Template:
            ...     return t
            >>> f()
            # Called main_template()
            Template(name='main')

        By default, the dependency does not have any :py:class:`.Scope`. So it's re-computed on each
        access:

        .. doctest:: lib_lazy_lazy

            >>> world[main_template()]
            Template(name='main')
            >>> f() is world[main_template()]
            False

        It is also possible to call the function with arguments:

        .. doctest:: lib_lazy_lazy

            >>> @lazy
            ... def template(name: str) -> Template:
            ...     return Template(name=name)
            >>> @inject
            ... def f(t: Template = inject[template(name='test')]) -> Template:
            ...     return t
            >>> f()
            Template(name='test')

        When using it with a :py:class:`.Scope` arguments are taken into account. Hence, they must be
        hashable.

        .. doctest:: lib_lazy_lazy

            >>> @lazy(lifetime='singleton')
            ... def template(name: str) -> Template:
            ...     return Template(name=name)
            >>> world[template(name='hello')] is world[template(name='hello')]
            True

        .. note::

            The original function is still accessible through :code:`__wrapped__`. Unfortunately this
            cannot be typed properly without leading to issues when wrapping methods typically.

        Args:
            __func: **/positional-only/** Function to wrap, which will be called lazily for
                dependencies.
            lifetime: :py:class:`.Scope`, or its lowercase name, if any of the dependency. Defaults to
                :py:obj:`None`, the dependency value is re-computed each time.
            inject: Can be used to prevent any injection by specifying :py:obj:`None`. Otherwise, the
                function will be injected if not yet already.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. When :code:`ignore_type_hints` is
                :py:obj:`True`, this features cannot be used. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            catalog: :py:class:`.Catalog` in which the dependency should be registered. Defaults to
                :py:obj:`.world`

        Returns:
            A :py:class:`.LazyWrappedFunction` or a function decorator to create it.
        """
        ...

    @overload
    def method(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> Callable[[Callable[Concatenate[Any, P], T]], LazyMethod[P, T]]:
        ...

    @overload
    def method(
        self,
        __func: Callable[Concatenate[Any, P], T],
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyMethod[P, T]:
        ...

    def method(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        ...

    @overload
    def property(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> Callable[[Callable[[Any], T]], LazyProperty[T]]:
        ...

    @overload
    def property(
        self,
        __func: Callable[[Any], T],
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyProperty[T]:
        ...

    def property(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        ...

    @overload
    def value(
        self,
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> Callable[[Callable[[], T] | staticmethod[Callable[[], T]]], LazyProperty[T]]:
        ...

    @overload
    def value(
        self,
        __func: Callable[[], T] | staticmethod[Callable[[], T]],
        *,
        lifetime: LifetimeType = ...,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> LazyValue[T]:
        ...

    def value(
        self,
        __func: object = None,
        *,
        lifetime: LifetimeType = "transient",
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        ...


@API.public
def is_lazy(__obj: object) -> bool:
    from ._lazy import LazyWrapper

    return isinstance(__obj, LazyWrapper)


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class DecoratorLazyFunction(Protocol):
    @overload
    def __call__(self, __func: staticmethod[Callable[P, T]]) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(self, __func: Callable[P, T]) -> LazyFunction[P, T]:
        ...

    def __call__(self, __func: object) -> object:
        ...
