import functools
from typing import Callable, Sequence

from .._internal.utils import SlotsReprMixin
from ..core import DependencyContainer
from ..exceptions import DependencyNotFoundError

compiled = False


class Injection(SlotsReprMixin):
    """
    Maps an argument name to its dependency and if the injection is required,
    which is equivalent to no default argument.
    """
    __slots__ = ('arg_name', 'required', 'dependency')

    def __init__(self, arg_name: str, required: bool, dependency):
        self.arg_name = arg_name
        self.required = required
        self.dependency = dependency


class InjectionBlueprint(SlotsReprMixin):
    """
    Stores all the injections for a function.
    """
    __slots__ = ('injections',)

    def __init__(self, injections: Sequence[Injection]):
        self.injections = injections


class InjectedWrapper:
    """
    Wrapper which injects all the dependencies not supplied in the passed
    arguments. An InjectionBlueprint is used to store the mapping of the
    arguments to their dependency if any and if the injection is required.
    """

    def __init__(self,
                 blueprint: InjectionBlueprint,
                 wrapped: Callable,
                 skip_self: bool = False):
        """
        Args:
            blueprint: Injection blueprint for the underlying function
            wrapped:  real function to be called
            skip_self:  whether the first argument must be skipped. Used internally
        """
        self.__wrapped__ = wrapped
        self.__blueprint = blueprint
        self.__injection_offset = 1 if skip_self else 0
        functools.wraps(wrapped, updated=())(self)

    def __call__(self, *args, **kwargs):
        from .state import get_container
        kwargs = _inject_kwargs(
            get_container(),
            self.__blueprint,
            self.__injection_offset + len(args),
            kwargs
        )
        return self.__wrapped__(*args, **kwargs)

    def __get__(self, instance, owner):
        return InjectedBoundWrapper(
            self.__blueprint,
            self.__wrapped__.__get__(instance, owner),
            isinstance(self.__wrapped__, classmethod)
            or (not isinstance(self.__wrapped__, staticmethod) and instance is not None)
        )

    def __getattr__(self, item):
        return getattr(self.__wrapped__, item)


class InjectedBoundWrapper(InjectedWrapper):
    """
    Behaves like Python bound methods. Unsure whether this is really necessary
    or not.
    """

    def __get__(self, instance, owner):
        return self  # pragma: no cover


def _inject_kwargs(container: DependencyContainer,
                   blueprint: InjectionBlueprint,
                   offset: int,
                   kwargs: dict) -> dict:
    """
    Does the actual injection of the dependencies. Used by InjectedCallableWrapper.
    """
    dirty_kwargs = False
    for injection in blueprint.injections[offset:]:
        if injection.dependency is not None and injection.arg_name not in kwargs:
            try:
                arg = container.get(injection.dependency)
                if not dirty_kwargs:
                    kwargs = kwargs.copy()
                    dirty_kwargs = True
                kwargs[injection.arg_name] = arg
            except DependencyNotFoundError:
                if injection.required:
                    raise

    return kwargs
