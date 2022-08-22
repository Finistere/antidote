from __future__ import annotations

import dataclasses
import inspect
from typing import Any, Awaitable, Callable, cast, TYPE_CHECKING, TypeVar

from typing_extensions import ParamSpec, TypeGuard

from ..._internal import API, Default
from .onion import CatalogOnionImpl, NotFoundSentinel
from .wrapper import current_catalog_onion, InjectedWrapper

if TYPE_CHECKING:
    from .._catalog import CatalogOnion
    from .._injection import InjectionBlueprint

__all__ = [
    "wrap",
    "unwrap",
    "is_wrapper",
    "rewrap",
    "create_public_private",
    "current_catalog_onion",
    "compiled",
    "is_catalog_onion",
    "NotFoundSentinel",
]

P = ParamSpec("P")
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

compiled = False


@API.private
def create_public_private(
    *, public_name: str, private_name: str
) -> tuple[CatalogOnion, CatalogOnion]:
    return CatalogOnionImpl.create_public_private(
        public_name=public_name, private_name=private_name
    )


@API.private
def wrap(
    wrapped: F,
    *,
    blueprint: InjectionBlueprint,
    maybe_app_catalog_onion: CatalogOnion | None,
    hardwired: bool,
) -> F:
    from .wrapper import AsyncInjectedWrapper, SyncInjectedWrapper

    assert maybe_app_catalog_onion is None or isinstance(maybe_app_catalog_onion, CatalogOnionImpl)

    if inspect.iscoroutinefunction(wrapped):
        out: object = AsyncInjectedWrapper(
            __wrapped__=wrapped,
            maybe_app_catalog_onion=maybe_app_catalog_onion,
            blueprint=blueprint,
            wrapped=cast(Callable[..., Awaitable[object]], wrapped),
            hardwired=hardwired,
        )
    else:
        out = SyncInjectedWrapper(
            __wrapped__=wrapped,
            maybe_app_catalog_onion=maybe_app_catalog_onion,
            blueprint=blueprint,
            wrapped=wrapped,
            hardwired=hardwired,
        )

    return cast(F, out)


@API.private
def unwrap(
    wrapper: Callable[P, T]
) -> tuple[Callable[P, T], CatalogOnion | None, InjectionBlueprint] | None:
    from .._injection import InjectionBlueprint

    maybe_blueprint: InjectionBlueprint | None = getattr(wrapper, "__antidote_blueprint__", None)
    if maybe_blueprint is not None and isinstance(maybe_blueprint, InjectionBlueprint):
        blueprint: InjectionBlueprint = maybe_blueprint
        maybe_app_catalog_onion: CatalogOnion | None = getattr(
            wrapper, "__antidote_maybe_app_catalog_onion__"
        )
        wrapped: Callable[P, T] = getattr(wrapper, "__antidote_wrapped__")
        return wrapped, maybe_app_catalog_onion, blueprint
    return None


@API.private
def rewrap(
    wrapper: Callable[..., Any],
    maybe_app_catalog_onion: CatalogOnion | None,
    inject_self: bool | Default,
) -> None:
    if is_wrapper(wrapper):
        assert maybe_app_catalog_onion is None or isinstance(
            maybe_app_catalog_onion, CatalogOnionImpl
        )
        if not wrapper.__antidote_hardwired__:
            wrapper.__antidote_maybe_app_catalog_onion__ = maybe_app_catalog_onion
        if inject_self is not Default.sentinel:
            if wrapper.__antidote_blueprint__.inject_self != inject_self:
                wrapper.__antidote_blueprint__ = dataclasses.replace(
                    wrapper.__antidote_blueprint__, inject_self=inject_self
                )


@API.private
def is_wrapper(x: object) -> TypeGuard[InjectedWrapper]:
    # Cannot use isinstance as we're overriding __class__. It doesn't work in Python 3.7 but did
    # work in 3.10.
    from .._injection import InjectionBlueprint

    maybe_blueprint = getattr(x, "__antidote_blueprint__", None)
    return maybe_blueprint is not None and isinstance(maybe_blueprint, InjectionBlueprint)


@API.private
def is_catalog_onion(x: object) -> TypeGuard[CatalogOnion]:
    return isinstance(x, CatalogOnionImpl)
