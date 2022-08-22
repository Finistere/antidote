from __future__ import annotations

import dataclasses
from contextvars import ContextVar, copy_context, Token
from typing import Any, Awaitable, Callable, TYPE_CHECKING

from ..._internal import API, wraps_frozen
from ..._internal.typing import Function
from .onion import CatalogOnionImpl, current_context, ProvideContext

if TYPE_CHECKING:
    from .._injection import Injection, InjectionBlueprint

__all__ = [
    "InjectedWrapper",
    "AsyncInjectedWrapper",
    "SyncInjectedWrapper",
    "current_catalog_onion",
]

current_catalog_onion = ContextVar[CatalogOnionImpl]("current_catalog")


@API.private
class InjectedWrapper:
    __slots__ = (
        "__antidote_wrapped__",
        "__antidote_maybe_app_catalog_onion__",
        "__antidote_hardwired__",
        "__antidote_blueprint__",
        "__antidote_bound_method__",
        "__dict__",
    )
    __wrapped__: object
    __antidote_wrapped__: Function[..., Any]
    __antidote_maybe_app_catalog_onion__: CatalogOnionImpl | None
    __antidote_hardwired__: bool
    __antidote_blueprint__: InjectionBlueprint
    __antidote_bound_method__: bool

    def __init__(
        self,
        __wrapped__: object,
        maybe_app_catalog_onion: CatalogOnionImpl | None,
        hardwired: bool,
        blueprint: InjectionBlueprint,
        wrapped: Callable[..., Any],
        bound_method: bool = False,
    ) -> None:
        self.__antidote_wrapped__ = wrapped
        self.__antidote_maybe_app_catalog_onion__ = maybe_app_catalog_onion
        self.__antidote_hardwired__ = hardwired
        self.__antidote_blueprint__ = blueprint
        self.__antidote_bound_method__ = bound_method
        wraps_frozen(__wrapped__)(self)

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
        blueprint = self.__antidote_blueprint__
        if blueprint.injections and blueprint.inject_self:
            injections: list[Injection] = list(blueprint.injections)
            injections[0] = dataclasses.replace(injections[0], dependency=owner)
            self.__antidote_blueprint__ = dataclasses.replace(
                blueprint, injections=tuple(injections)
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
            self.__wrapped__,
            self.__antidote_maybe_app_catalog_onion__,
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
            self.__wrapped__,
            self.__antidote_maybe_app_catalog_onion__,
            self.__antidote_hardwired__,
            self.__antidote_blueprint__,
            self.__antidote_wrapped__.__get__(instance, owner),
            instance is not None,
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
    onion_token: Token[CatalogOnionImpl] | None = None
    context_token: Token[ProvideContext] | None = None
    maybe_app_onion = wrapper.__antidote_maybe_app_catalog_onion__
    blueprint = wrapper.__antidote_blueprint__
    bound_method = wrapper.__antidote_bound_method__
    offset = int(bound_method) + len(args)
    if blueprint.positional_arguments_count < offset:
        offset = blueprint.positional_arguments_count

    if maybe_app_onion is None:
        layer = current_catalog_onion.get().layer
    else:
        onion_token = current_catalog_onion.set(maybe_app_onion)
        layer = maybe_app_onion.layer
    context: ProvideContext | None = current_context.get(None)
    if context is None:
        context = ProvideContext()
        context_token = current_context.set(context)
    try:
        kwargs = kwargs.copy()
        if blueprint.inject_self and not bound_method:
            self_injection = blueprint.injections[0]
            self = layer.provide(self_injection.dependency, self_injection.default, context)
            args = (self, *args)
            offset += 1
        for injection in blueprint.injections[offset:]:
            if injection.dependency is not None and injection.arg_name not in kwargs:
                value = layer.provide(injection.dependency, injection.default, context)
                kwargs[injection.arg_name] = value

        return wrapper.__antidote_wrapped__(*args, **kwargs)
    finally:
        if onion_token is not None:
            current_catalog_onion.reset(onion_token)
        if context_token is not None:
            current_context.reset(context_token)
            context.release()
