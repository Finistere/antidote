import functools
import inspect
from typing import Any, Awaitable, Callable, cast, Dict, Hashable, Sequence

from . import API
from .state import current_container
from .utils import FinalImmutable
from ..core.container import Container
from ..core.exceptions import DependencyNotFoundError

compiled = False


@API.private
class Injection(FinalImmutable):
    """
    Maps an argument name to its dependency and if the injection is required,
    which is equivalent to no default argument.
    """
    __slots__ = ('arg_name', 'required', 'dependency', 'default_value')
    arg_name: str
    required: bool
    dependency: Hashable
    default_value: object

    def __init__(self,
                 *,
                 arg_name: str,
                 required: bool,
                 default: object,
                 dependency: Hashable
                 ) -> None:
        super().__init__(
            arg_name=arg_name,
            required=required,
            dependency=dependency,
            default_value=default
        )


@API.private
class InjectionBlueprint(FinalImmutable):
    """
    Stores all the injections for a function.
    """
    __slots__ = ('injections',)
    injections: Sequence[Injection]

    def is_empty(self) -> bool:
        return all(injection.dependency is None for injection in self.injections)


@API.private
def build_wrapper(blueprint: InjectionBlueprint,
                  wrapped: Callable[..., object],
                  skip_self: bool = False) -> Callable[..., object]:
    if inspect.iscoroutinefunction(wrapped):
        return AsyncInjectedWrapper(blueprint,
                                    cast(Callable[..., Awaitable[object]], wrapped),
                                    skip_self)
    return SyncInjectedWrapper(blueprint, wrapped, skip_self)


@API.private
def get_wrapper_injections(wrapper: Callable[..., object]) -> Dict[str, Hashable]:
    if not isinstance(wrapper, InjectedWrapper):
        raise TypeError(f"Argument must be an {InjectedWrapper}")

    if isinstance(wrapper, SyncInjectedWrapper):
        prefix = f"_{SyncInjectedWrapper.__name__}"
    else:
        prefix = f"_{AsyncInjectedWrapper.__name__}"
    blueprint: InjectionBlueprint = getattr(wrapper,
                                            f"{prefix}__blueprint")

    return {inj.arg_name: inj.dependency for inj in blueprint.injections if
            inj.dependency is not None}


@API.private
def is_wrapper(x: object) -> bool:
    return isinstance(x, InjectedWrapper)


@API.private
def get_wrapped(x: object) -> object:
    assert isinstance(x, InjectedWrapper)
    return x.__wrapped__


@API.private
class InjectedWrapper:
    __wrapped__: object

    def __init__(self, wrapped: Callable[..., object]) -> None:
        self.__wrapped__ = wrapped
        functools.wraps(wrapped, updated=())(self)

    @property  # type: ignore
    def __class__(self) -> Any:
        return self.__wrapped__.__class__

    def __getattr__(self, item: str) -> object:
        return getattr(self.__wrapped__, item)


@API.private
class SyncInjectedWrapper(InjectedWrapper):
    """
    Wrapper which injects all the dependencies not supplied in the passed
    arguments. An InjectionBlueprint is used to store the mapping of the
    arguments to their dependency if any and if the injection is required.
    """
    __wrapped__: Callable[..., object]

    def __init__(self,
                 blueprint: InjectionBlueprint,
                 wrapped: Callable[..., object],
                 skip_self: bool = False):
        """
        Args:
            blueprint: Injection blueprint for the underlying function
            wrapped:  real function to be called
            skip_self:  whether the first argument must be skipped. Used internally
        """
        self.__blueprint = blueprint
        self.__injection_offset = 1 if skip_self else 0
        super().__init__(wrapped)

    def __call__(self, *args: object, **kwargs: object) -> object:
        kwargs = _inject_kwargs(
            current_container(),
            self.__blueprint,
            self.__injection_offset + len(args),
            kwargs
        )
        return self.__wrapped__(*args, **kwargs)

    def __get__(self, instance: object, owner: type) -> object:
        return SyncInjectedBoundWrapper(
            self.__blueprint,
            self.__wrapped__.__get__(instance, owner),
            instance is not None
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
    """
    Wrapper which injects all the dependencies not supplied in the passed
    arguments. An InjectionBlueprint is used to store the mapping of the
    arguments to their dependency if any and if the injection is required.
    """
    __wrapped__: Callable[..., Awaitable[object]]

    def __init__(self,
                 blueprint: InjectionBlueprint,
                 wrapped: Callable[..., Awaitable[object]],
                 skip_self: bool = False):
        """
        Args:
            blueprint: Injection blueprint for the underlying function
            wrapped:  real function to be called
            skip_self:  whether the first argument must be skipped. Used internally
        """
        self.__blueprint = blueprint
        self.__injection_offset = 1 if skip_self else 0
        super().__init__(wrapped)

    async def __call__(self, *args: object, **kwargs: object) -> object:
        kwargs = _inject_kwargs(
            current_container(),
            self.__blueprint,
            self.__injection_offset + len(args),
            kwargs
        )
        return await self.__wrapped__(*args, **kwargs)

    def __get__(self, instance: object, owner: type) -> object:
        return AsyncInjectedBoundWrapper(
            self.__blueprint,
            self.__wrapped__.__get__(instance, owner),
            instance is not None
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
def _inject_kwargs(container: Container,
                   blueprint: InjectionBlueprint,
                   offset: int,
                   kwargs: Dict[str, object]) -> Dict[str, object]:
    """
    Does the actual injection of the dependencies. Used by InjectedCallableWrapper.
    """
    dirty_kwargs = False
    for injection in blueprint.injections[offset:]:
        if injection.dependency is not None and injection.arg_name not in kwargs:
            try:
                arg = container.get(injection.dependency,
                                    injection.default_value)
                if not dirty_kwargs:
                    kwargs = kwargs.copy()
                    dirty_kwargs = True
                kwargs[injection.arg_name] = arg
            except DependencyNotFoundError:
                if injection.required:
                    raise

    return kwargs
