from typing import Callable

from .._internal.utils import SlotReprMixin
from ..container import DependencyContainer
from ..exceptions import DependencyNotFoundError


class InjectionBlueprint(SlotReprMixin):
    __slots__ = ('injections',)

    def __init__(self, injections):
        self.injections = injections


class Injection(SlotReprMixin):
    __slots__ = ('arg_name', 'required', 'dependency_id')

    def __init__(self, arg_name, required, dependency_id):
        self.arg_name = arg_name
        self.required = required
        self.dependency_id = dependency_id


class InjectedCallableWrapper:
    def __init__(self,
                 container: DependencyContainer,
                 blueprint: InjectionBlueprint,
                 wrapped: Callable,
                 skip_self: bool = False):
        self.__container = container
        self.__wrapped = wrapped
        self.__blueprint = blueprint
        self.__injection_offset = 1 if skip_self else 0

    def __call__(self, *args, **kwargs):
        kwargs = _inject_kwargs(
            self.__container,
            self.__blueprint,
            self.__injection_offset + len(args),
            kwargs
        )
        return self.__wrapped(*args, **kwargs)

    def __get__(self, instance, owner):
        skip_self = instance is not None
        func = self.__wrapped.__get__(instance, owner)
        return InjectedBoundCallableWrapper(self.__container, self.__blueprint,
                                            func, skip_self=skip_self)


class InjectedBoundCallableWrapper(InjectedCallableWrapper):
    def __get__(self, instance, owner):
        return self


def _inject_kwargs(container: DependencyContainer,
                   blueprint: InjectionBlueprint,
                   offset: int,
                   kwargs: dict) -> dict:
    dirty_kwargs = False
    for injection in blueprint.injections[offset:]:
        if injection.dependency_id is not None and injection.arg_name not in kwargs:
            instance = container.provide(injection.dependency_id)
            if instance is not container.SENTINEL:
                if not dirty_kwargs:
                    kwargs = kwargs.copy()
                    dirty_kwargs = True
                kwargs[injection.arg_name] = instance
            elif injection.required:
                raise DependencyNotFoundError(injection.dependency_id)

    return kwargs
