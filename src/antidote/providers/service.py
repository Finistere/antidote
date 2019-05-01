import inspect
from typing import Any, Callable, Dict, Optional, Tuple, Union

from .._internal.utils import SlotsReprMixin
from ..core import DependencyContainer, DependencyInstance, DependencyProvider
from ..exceptions import DuplicateDependencyError


class LazyFactory(SlotsReprMixin):
    __slots__ = ('dependency',)

    def __init__(self, dependency):
        self.dependency = dependency


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
    __slots__ = ('wrapped', 'args', 'kwargs')

    __str__ = SlotsReprMixin.__repr__

    def __init__(self, *args, **kwargs):
        """
        Args:
            *args: The first argument is the dependency, all others are passed
                on to the factory.
            **kwargs: Passed on to the factory.
        """
        if not args:
            raise TypeError("At least the dependency and one additional argument "
                            "are mandatory.")

        self.wrapped = args[0]
        self.args = args[1:]  # type: Tuple
        self.kwargs = kwargs  # type: Dict

        if not self.args and not self.kwargs:
            raise TypeError("Without additional arguments, Build must not be used.")

    def __hash__(self):
        try:
            # Try most precise hash first
            return hash((self.wrapped, self.args, tuple(self.kwargs.items())))
        except TypeError:
            # If type error, return the best error-free hash possible
            return hash((self.wrapped, len(self.args), tuple(self.kwargs.keys())))

    def __eq__(self, other):
        return isinstance(other, Build) \
               and (self.wrapped is other.wrapped or self.wrapped == other.wrapped) \
               and self.args == other.args \
               and self.kwargs == self.kwargs  # noqa


class ServiceProvider(DependencyProvider):
    """
    Provider managing factories. Also used to register classes directly.
    """
    bound_dependency_types = (Build,)

    def __init__(self, container: DependencyContainer):
        super().__init__(container)
        self._service_to_factory = dict()  # type: Dict[Any, ServiceFactory]

    def __repr__(self):
        return "{}(factories={!r})".format(type(self).__name__,
                                           tuple(self._service_to_factory.keys()))

    def provide(self, dependency) -> Optional[DependencyInstance]:
        if isinstance(dependency, Build):
            service = dependency.wrapped
        else:
            service = dependency

        try:
            factory = self._service_to_factory[service]  # type: ServiceFactory
        except KeyError:
            return None

        if isinstance(dependency, Build):
            args = dependency.args
            kwargs = dependency.kwargs
        else:
            args = tuple()
            kwargs = dict()

        if factory.takes_dependency:
            args = (service,) + args

        if factory.func is None:
            factory.func = self._container.get(factory.lazy_dependency)
            factory.lazy_dependency = None

        return DependencyInstance(factory.func(*args, **kwargs),
                                  singleton=factory.singleton)

    def register(self,
                 service: type,
                 factory: Union[Callable, LazyFactory] = None,
                 singleton: bool = True,
                 takes_dependency: bool = False):
        """
        Register a factory for a dependency.

        Args:
            service: dependency to register.
            factory: Callable used to instantiate the dependency.
            singleton: Whether the dependency should be mark as singleton or
                not for the :py:class:`~..core.DependencyContainer`.
            takes_dependency: If True, the factory will be given the requested
                dependency as its first arguments. This allows re-using the
                same factory for different dependencies.
        """
        if not inspect.isclass(service):
            raise TypeError("A service must be a class, not a {!r}".format(service))

        if isinstance(factory, LazyFactory):
            service_factory = ServiceFactory(
                singleton=singleton,
                func=None,
                lazy_dependency=factory.dependency,
                takes_dependency=takes_dependency
            )
        elif factory is None or callable(factory):
            service_factory = ServiceFactory(
                singleton=singleton,
                func=service if factory is None else factory,
                lazy_dependency=None,
                takes_dependency=takes_dependency
            )
        else:
            raise TypeError("factory must be callable or be a Lazy dependency.")

        if service in self._service_to_factory:
            raise DuplicateDependencyError(service, self._service_to_factory[service])

        self._service_to_factory[service] = service_factory

        return service


# TODO: define better __str__()
class ServiceFactory(SlotsReprMixin):
    """
    Not part of the public API.

    Only used by the FactoryProvider to store information on how the factory
    has to be used.
    """
    __slots__ = ('singleton', 'func', 'takes_dependency', 'lazy_dependency')

    def __init__(self,
                 singleton: bool,
                 func: Optional[Callable],
                 lazy_dependency: Optional[Any],
                 takes_dependency: bool):
        assert func is not None or lazy_dependency is not None
        self.singleton = singleton
        self.func = func
        self.lazy_dependency = lazy_dependency
        self.takes_dependency = takes_dependency
