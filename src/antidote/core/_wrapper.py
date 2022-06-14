from __future__ import annotations

import dataclasses
import inspect
from contextvars import ContextVar, copy_context, Token
from typing import Any, Awaitable, Callable, cast, Tuple, TYPE_CHECKING, TypeVar

from typing_extensions import ParamSpec, TypeGuard

from .._internal import API, Default, wraps_frozen
from .._internal.typing import Function
from ._internal_catalog import InternalCatalog, NotFoundSentinel
from .exceptions import DependencyNotFoundError

if TYPE_CHECKING:
    from ._injection import Injection, InjectionBlueprint

__all__ = ["wrap", "unwrap", "is_wrapper", "rewrap"]

compiled = False
current_catalog_context = ContextVar[InternalCatalog]("current_catalog")

F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")
T = TypeVar("T")


@API.private
def wrap(
    wrapped: F, *, blueprint: InjectionBlueprint, catalog: InternalCatalog | None, hardwired: bool
) -> F:
    if inspect.iscoroutinefunction(wrapped):
        return cast(
            F,
            AsyncInjectedWrapper(
                catalog=catalog,
                blueprint=blueprint,
                wrapped=cast(Callable[..., Awaitable[object]], wrapped),
                hardwired=hardwired,
            ),
        )
    return cast(
        F,
        SyncInjectedWrapper(
            catalog=catalog, blueprint=blueprint, wrapped=wrapped, hardwired=hardwired
        ),
    )


@API.private
def unwrap(
    wrapper: Callable[P, T]
) -> Tuple[Callable[P, T], InternalCatalog | None, InjectionBlueprint] | None:
    from ._injection import InjectionBlueprint

    maybe_blueprint: InjectionBlueprint | None = getattr(wrapper, "__antidote_blueprint__", None)
    if maybe_blueprint is not None and isinstance(maybe_blueprint, InjectionBlueprint):
        blueprint: InjectionBlueprint = maybe_blueprint
        catalog: InternalCatalog | None = getattr(wrapper, "__antidote_catalog__")
        wrapped: Callable[P, T] = getattr(wrapper, "__antidote_wrapped__")
        return wrapped, catalog, blueprint
    return None


@API.private
def rewrap(
    wrapper: Callable[..., Any], catalog: InternalCatalog | None, inject_self: bool | Default
) -> None:
    if is_wrapper(wrapper):
        if not wrapper.__antidote_hardwired__:
            wrapper.__antidote_catalog__ = catalog
        if inject_self is not Default.sentinel:
            if wrapper.__antidote_blueprint__.inject_self != inject_self:
                wrapper.__antidote_blueprint__ = dataclasses.replace(
                    wrapper.__antidote_blueprint__, inject_self=inject_self
                )


@API.private
def is_wrapper(x: object) -> TypeGuard[InjectedWrapper]:
    # Cannot use isinstance as we're overriding __class__. It doesn't work in Python 3.7 but did
    # work in 3.10.
    return unwrap(cast(Any, x)) is not None


@API.private
class InjectedWrapper:
    __slots__ = (
        "__antidote_wrapped__",
        "__antidote_catalog__",
        "__antidote_hardwired__",
        "__antidote_blueprint__",
        "__antidote_bound_method__",
        "__dict__",
    )
    __wrapped__: object
    __antidote_wrapped__: Function[..., Any]
    __antidote_catalog__: InternalCatalog | None
    __antidote_hardwired__: bool
    __antidote_blueprint__: InjectionBlueprint
    __antidote_bound_method__: bool

    def __init__(
        self,
        catalog: InternalCatalog | None,
        hardwired: bool,
        blueprint: InjectionBlueprint,
        wrapped: Callable[..., Any],
        bound_method: bool = False,
    ) -> None:
        self.__wrapped__ = wrapped
        self.__antidote_wrapped__ = wrapped
        self.__antidote_catalog__ = catalog
        self.__antidote_hardwired__ = hardwired
        self.__antidote_blueprint__ = blueprint
        self.__antidote_bound_method__ = bound_method
        wraps_frozen(wrapped)(self)

    @property  # type: ignore
    def __class__(self) -> Any:
        return self.__antidote_wrapped__.__class__

    def __getattr__(self, item: str) -> object:
        return getattr(self.__antidote_wrapped__, item)

    def __repr__(self) -> str:
        return f"<injected {self.__antidote_wrapped__!r}>"

    def __str__(self) -> str:
        return str(self.__antidote_wrapped__)

    def __set_name__(self, owner: type, name: str) -> None:
        if self.__antidote_blueprint__.injections and self.__antidote_blueprint__.inject_self:
            injections: list[Injection] = list(self.__antidote_blueprint__.injections)
            injections[0] = dataclasses.replace(injections[0], dependency=owner)
            self.__antidote_blueprint__ = dataclasses.replace(
                self.__antidote_blueprint__,
                injections=tuple(injections),
            )
        try:
            self.__antidote_wrapped__.__set_name__(owner, name)  # type: ignore
        except AttributeError:
            pass


@API.private
class SyncInjectedWrapper(InjectedWrapper):
    __antidote_wrapped__: Callable[..., object]

    def __call__(self, *args: object, **kwargs: object) -> object:
        return copy_context().run(
            _call,
            self,
            args,
            kwargs,
        )

    def __get__(self, instance: object, owner: type) -> object:
        return SyncInjectedBoundWrapper(
            self.__antidote_catalog__,
            self.__antidote_hardwired__,
            self.__antidote_blueprint__,
            self.__antidote_wrapped__.__get__(instance, owner),
            instance is not None,
        )


@API.private
class SyncInjectedBoundWrapper(SyncInjectedWrapper):
    """
    Behaves like Python bound methods. Unsure whether this is really necessary
    or not.
    """

    def __get__(self, instance: object, owner: type) -> object:
        return self  # pragma: no cover


@API.private
class AsyncInjectedWrapper(InjectedWrapper):
    __antidote_wrapped__: Callable[..., Awaitable[object]]

    async def __call__(self, *args: object, **kwargs: object) -> object:
        return await copy_context().run(
            _call,
            self,
            args,
            kwargs,
        )

    def __get__(self, instance: object, owner: type) -> object:
        return AsyncInjectedBoundWrapper(
            self.__antidote_catalog__,
            self.__antidote_hardwired__,
            self.__antidote_blueprint__,
            self.__antidote_wrapped__.__get__(instance, owner),
            instance is not None or self.__antidote_blueprint__.inject_self,
        )


@API.private
class AsyncInjectedBoundWrapper(AsyncInjectedWrapper):
    """
    Behaves like Python bound methods. Unsure whether this is really necessary
    or not.
    """

    def __get__(self, instance: object, owner: type) -> object:
        return self  # pragma: no cover


@API.private
def _call(
    wrapper: InjectedWrapper,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> Any:
    token: Token[InternalCatalog] | None = None
    catalog = wrapper.__antidote_catalog__
    blueprint = wrapper.__antidote_blueprint__
    bound_method = wrapper.__antidote_bound_method__
    offset = min(
        blueprint.positional_arguments_count, int(blueprint.inject_self or bound_method) + len(args)
    )

    if catalog is None:
        catalog = current_catalog_context.get()
    else:
        token = current_catalog_context.set(catalog)
    try:
        kwargs = kwargs.copy()
        with catalog.current_context() as context:
            if blueprint.inject_self and not bound_method:
                self_injection = blueprint.injections[0]
                self = catalog.provide(self_injection.dependency, self_injection.default, context)
                if self is NotFoundSentinel:
                    raise DependencyNotFoundError(
                        dependency=self_injection.dependency, catalog=catalog
                    )
                args = (self, *args)
            for injection in blueprint.injections[offset:]:
                if injection.dependency is not None and injection.arg_name not in kwargs:
                    value = catalog.provide(injection.dependency, injection.default, context)
                    if value is not NotFoundSentinel:
                        kwargs[injection.arg_name] = value
                    elif injection.required:
                        raise DependencyNotFoundError(
                            dependency=injection.dependency, catalog=catalog
                        )

        return wrapper.__antidote_wrapped__(*args, **kwargs)
    finally:
        if token is not None:
            current_catalog_context.reset(token)
