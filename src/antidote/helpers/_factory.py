from typing import (Any, Callable, Dict, get_type_hints, Iterable, TypeVar, Union)

from .inject import inject
from .register import register
from .wire import wire, Wiring
from .._internal.utils import API, SlotsReprMixin
from ..providers.factory import Build, FactoryProvider
from ..providers.tag import Tag, TagProvider

F = TypeVar('F', bound=Callable[..., Any])


@API.private
class FactoryMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        mcls.__register_factory(cls)
        return cls

    def __rmatmul__(cls, dependency) -> Build:
        return dependency @ PreBuild(cls, cls.__supported_dependency)

    def with_kwargs(cls, **kwargs) -> 'PreBuild':
        return PreBuild(cls, cls.__supported_dependency, kwargs)

    @property
    def __supported_dependency(cls):
        return get_type_hints(cls.__call__).get('return')

    @staticmethod
    @inject
    def __register_factory(cls,
                           factory_provider: FactoryProvider,
                           tag_provider: TagProvider = None):
        if '__call__' not in dir(cls):
            raise TypeError(f"The class {cls} must implement __call__()")

        wiring: Wiring = cls.wiring
        singleton: bool = cls.singleton
        tags: Iterable[Union[str, Tag]] = cls.tags

        dependency = get_type_hints(cls.__call__).get('return')
        if dependency is None:
            raise ValueError("The return annotation is necessary on __call__."
                             "It is used a the dependency.")

        wire_raise_on_missing = True
        if wiring.is_auto():
            wiring = Wiring(
                methods=('__call__', '__init__'),
                dependencies=wiring.dependencies,
                use_names=wiring.use_names,
                use_type_hints=wiring.use_type_hints,
                wire_super=wiring.wire_super
            )
            wire_raise_on_missing = False

        if wiring.methods:
            wire(cls, wiring=wiring, raise_on_missing_method=wire_raise_on_missing)

        obj = register(cls, auto_wire=False, singleton=True)
        factory_provider.register_providable_factory(
            dependency=dependency,
            singleton=singleton,
            takes_dependency=False,
            factory_dependency=obj
        )

        if tags is not None:
            if tag_provider is None:
                raise RuntimeError("No TagProvider registered, cannot use tags.")
            tag_provider.register(dependency=dependency, tags=tags)


@API.private
class LambdaFactory(SlotsReprMixin):
    __slots__ = ('__factory',)

    def __init__(self, factory: Callable):
        self.__factory = factory

    @property
    def __supported_dependency(self):
        return get_type_hints(self.__factory).get('return')

    def __call__(self, *args, **kwargs):
        return self.__factory(*args, **kwargs)

    def __rmatmul__(self, dependency) -> Build:
        return dependency @ PreBuild(self, self.__supported_dependency)

    def with_kwargs(self, **kwargs) -> 'PreBuild':
        return PreBuild(self, self.__supported_dependency, kwargs)


@API.private
class PreBuild(SlotsReprMixin):
    __slots__ = ('factory', 'supported_dependency', 'kwargs')

    def __init__(self, factory, supported_dependency, kwargs: Dict = None):
        self.factory = factory
        self.supported_dependency = supported_dependency
        self.kwargs = kwargs

    def __rmatmul__(self, dependency) -> Build:
        if dependency != self.supported_dependency:
            raise ValueError(f"Factory {self.factory!r} cannot build {dependency!r}, "
                             f"only {self.supported_dependency!r}.")
        return Build(dependency, self.kwargs)
