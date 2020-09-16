import threading
from typing import Callable, Dict, get_type_hints, Hashable, Optional, Protocol, TypeVar

from .._internal.utils import API, SlotsReprMixin
from ..core import DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError, FrozenWorldError

F = TypeVar("F", bound=Callable[..., object])


class FactoryProtocol(Protocol):
    def __rmatmul__(self, dependency) -> 'Build':
        pass

    def with_kwargs(self, **kwargs) -> 'PreBuild':
        pass

    __call__: F


@API.public
class FactoryMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)

        if '__call__' not in dir(cls):
            raise TypeError(f"The class {cls} must implement __call__()")

        return cls

    def __rmatmul__(cls, dependency) -> 'Build':
        return dependency @ PreBuild(cls, cls.__supported_dependency)

    def with_kwargs(cls, **kwargs) -> 'PreBuild':
        return PreBuild(cls, cls.__supported_dependency, kwargs)

    @API.private
    @property
    def __supported_dependency(cls):
        return get_type_hints(cls.__call__).get('return')


@API.public
class Factory(metaclass=FactoryMeta):
    pass


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

    def __rmatmul__(self, dependency) -> 'Build':
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

    def __rmatmul__(self, dependency) -> 'Build':
        if dependency != self.supported_dependency:
            raise ValueError(f"Factory {self.factory!r} cannot build {dependency!r}, "
                             f"only {self.supported_dependency!r}.")
        return Build(dependency, self.kwargs)


@API.public
class Build(SlotsReprMixin):
    """
    Custom Dependency wrapper used to pass arguments to the factory used to
    create the actual dependency.

    .. doctest::

        >>> from antidote import Build, register, world
        >>> @register
        ... class Dummy:
        ...     def __init__(self, name=None):
        ...         self.name = name
        >>> dummy = world.get(Build(Dummy, name='me'))
        >>> dummy.name
        'me'

    With no arguments, that is to say :code:`Build(x)`, it is equivalent to
    :code:`x` for the :py:class:`~.core.DependencyContainer`.
    """
    __slots__ = ('dependency', 'kwargs', '__hash')

    def __init__(self, dependency: Hashable, kwargs: Dict = None):
        """
        Args:
            *args: The first argument is the dependency, all others are passed
                on to the factory.
            **kwargs: Passed on to the factory.
        """
        self.dependency: Hashable = dependency
        self.kwargs: Dict = kwargs or None

        if self.kwargs:
            try:
                # Try most precise hash first
                self.__hash = hash((self.dependency, tuple(self.kwargs.items())))
            except TypeError:
                # If type error, return the best error-free hash possible
                self.__hash = hash((self.dependency, tuple(self.kwargs.keys())))
        else:
            self.__hash = hash((Build, self.dependency))

    def __hash__(self):
        return self.__hash

    def __eq__(self, other):
        return isinstance(other, Build) \
               and (
                       self.dependency is other.dependency or self.dependency == other.dependency) \
               and self.kwargs == self.kwargs  # noqa


@API.private
class FactoryProvider(DependencyProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """

    def __init__(self):
        super().__init__()
        self.__builders: Dict[Hashable, Builder] = dict()
        self.__freeze_lock = threading.RLock()
        self.__frozen = False

    def __repr__(self):
        return f"{type(self).__name__}(factories={tuple(self.__builders.keys())!r})"

    def freeze(self):
        with self.__freeze_lock:
            self.__frozen = True

    def clone(self) -> DependencyProvider:
        f = FactoryProvider()
        f.__builders = self.__builders.copy()
        return f

    def provide(self, build: Hashable, container: DependencyContainer
                ) -> Optional[DependencyInstance]:
        if isinstance(build, Build):
            try:
                builder: Builder = self.__builders[build.dependency]
            except KeyError:
                return None

            if builder.factory_dependency is not None:
                f = container.provide(builder.factory_dependency)
                factory = f.instance
                if f.singleton:
                    builder.factory_dependency = None
                    builder.factory = f.instance
            else:
                factory = builder.factory

            if builder.takes_dependency:
                instance = factory(build.dependency, **build.kwargs) \
                    if build.kwargs else factory(build.dependency)
            else:
                instance = factory(**build.kwargs) if build.kwargs else factory()

            return DependencyInstance(instance,
                                      singleton=builder.singleton)

    def register_class(self, class_: type, singleton: bool = True):
        """
        Register a class which is both dependency and factory.

        Args:
            class_: dependency to register.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
        """
        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add {class_} to a frozen world.")
            self.register_factory(dependency=class_, factory=class_,
                                  singleton=singleton, takes_dependency=False)
        return class_

    def register_factory(self,
                         dependency: Hashable,
                         factory: Callable,
                         singleton: bool = True,
                         takes_dependency: bool = False):
        """
        Registers a factory for a dependency.

        Args:
            dependency: dependency to register.
            factory: Callable used to instantiate the dependency.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
            takes_dependency: If True, the factory will be given the requested
                dependency as its first arguments. This allows re-using the
                same factory for different dependencies.
        """
        if dependency in self.__builders:
            raise DuplicateDependencyError(dependency,
                                           self.__builders[dependency])

        if callable(factory):
            with self.__freeze_lock:
                if self.__frozen:
                    raise FrozenWorldError(f"Cannot add {dependency} to a frozen world.")
                self.__builders[dependency] = Builder(singleton=singleton,
                                                      takes_dependency=takes_dependency,
                                                      factory=factory)
        else:
            raise TypeError(f"factory must be callable, not {type(factory)!r}.")

    def register_providable_factory(self,
                                    dependency: Hashable,
                                    factory_dependency: Hashable,
                                    singleton: bool = True,
                                    takes_dependency: bool = False):
        """
        Registers a lazy factory (retrieved only at the first instantiation) for
        a dependency.

        Args:
            dependency: dependency to register.
            factory_dependency: Dependency used to retrieve.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
            takes_dependency: If True, the factory will be given the requested
                dependency as its first arguments. This allows re-using the
                same factory for different dependencies.
        """
        if dependency in self.__builders:
            raise DuplicateDependencyError(dependency,
                                           self.__builders[dependency])

        with self.__freeze_lock:
            if self.__frozen:
                raise FrozenWorldError(f"Cannot add {dependency} to a frozen world.")
            self.__builders[dependency] = Builder(singleton=singleton,
                                                  takes_dependency=takes_dependency,
                                                  factory_dependency=factory_dependency)


@API.private
class Builder(SlotsReprMixin):
    """
    Not part of the public API.

    Only used by the FactoryProvider to store information on how the factory
    has to be used.
    """
    __slots__ = ('singleton', 'factory', 'takes_dependency', 'factory_dependency')

    def __init__(self,
                 singleton: bool,
                 takes_dependency: bool,
                 factory: Optional[Callable] = None,
                 factory_dependency: Optional[Hashable] = None):
        assert factory is not None or factory_dependency is not None
        self.singleton = singleton
        self.takes_dependency = takes_dependency
        self.factory = factory
        self.factory_dependency = factory_dependency
