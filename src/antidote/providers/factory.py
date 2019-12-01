from typing import Callable, Dict, Hashable, Optional

from .._internal.utils import SlotsReprMixin
from ..core import DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError


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
    __slots__ = ('dependency', 'kwargs', '_hash')

    __str__ = SlotsReprMixin.__repr__  # type: Callable[['Build'], str]

    def __init__(self, dependency: Hashable, **kwargs):
        """
        Args:
            *args: The first argument is the dependency, all others are passed
                on to the factory.
            **kwargs: Passed on to the factory.
        """
        self.dependency = dependency  # type: Hashable
        self.kwargs = kwargs  # type: Dict

        if not self.kwargs:
            raise TypeError("Without additional arguments, Build must not be used.")

        try:
            # Try most precise hash first
            self._hash = hash((self.dependency, tuple(self.kwargs.items())))
        except TypeError:
            # If type error, return the best error-free hash possible
            self._hash = hash((self.dependency, tuple(self.kwargs.keys())))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, Build) \
               and (self.dependency is other.dependency
                    or self.dependency == other.dependency) \
               and self.kwargs == self.kwargs  # noqa


class FactoryProvider(DependencyProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """
    bound_dependency_types = (Build,)

    def __init__(self, container: DependencyContainer):
        super().__init__(container)
        self._builders = dict()  # type: Dict[Hashable, Builder]

    def __repr__(self):
        return "{}(factories={!r})".format(type(self).__name__,
                                           tuple(self._builders.keys()))

    def provide(self, dependency: Hashable) -> Optional[DependencyInstance]:
        try:
            if isinstance(dependency, Build):
                builder = self._builders[dependency.dependency]  # type: Builder
            else:
                builder = self._builders[dependency]
        except KeyError:
            return None

        if builder.factory_dependency is not None:
            f = self._container.safe_provide(builder.factory_dependency)
            factory = f.instance
            if f.singleton:
                builder.factory_dependency = None
                builder.factory = f.instance
        else:
            factory = builder.factory

        if isinstance(dependency, Build):
            if builder.takes_dependency:
                instance = factory(dependency.dependency, **dependency.kwargs)
            else:
                instance = factory(**dependency.kwargs)
        else:
            if builder.takes_dependency:
                instance = factory(dependency)
            else:
                instance = factory()

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
        if dependency in self._builders:
            raise DuplicateDependencyError(dependency,
                                           self._builders[dependency])

        if callable(factory):
            self._builders[dependency] = Builder(singleton=singleton,
                                                 takes_dependency=takes_dependency,
                                                 factory=factory)
        else:
            raise TypeError("factory must be callable, not {!r}.".format(type(factory)))

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
        if dependency in self._builders:
            raise DuplicateDependencyError(dependency,
                                           self._builders[dependency])

        self._builders[dependency] = Builder(singleton=singleton,
                                             takes_dependency=takes_dependency,
                                             factory_dependency=factory_dependency)


# TODO: define better __str__()
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
