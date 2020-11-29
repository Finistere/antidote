import functools
import inspect
from typing import Callable, Iterable, TypeVar, Union

from ._implementation import ImplementationMeta
from ._internal import API
from ._providers import IndirectProvider
from .core import inject
from .core.injection import DEPENDENCIES_TYPE
from .service import Service

F = TypeVar('F', bound=Callable[[], type])
C = TypeVar('C', bound=type)


@API.experimental
class Implementation(Service, metaclass=ImplementationMeta, abstract=True):
    """
    Essentially syntactic sugar to define easily a single implementation for an interface.
    The class will automatically be defined as a :py:class:`~.Service`, hence it has the
    same features.

    .. doctest:: helpers_implementation_class

        >>> from antidote import world, Implementation
        >>> class Interface:
        ...     pass
        >>> class Impl(Interface, Implementation):
        ...     pass
        >>> world.get(Interface)
        <Impl ...>

    .. note::

        If you need to chose between multiple implementations use
        :py:func:`.implementation`.
    """


@API.public
def implementation(interface: type,
                   *,
                   permanent: bool = True,
                   auto_wire: bool = True,
                   dependencies: DEPENDENCIES_TYPE = None,
                   use_names: Union[bool, Iterable[str]] = None,
                   use_type_hints: Union[bool, Iterable[str]] = None) -> Callable[[F], F]:
    """
    Function decorator which decides which implementation should be used for
    :code:`interface`.

    The underlying function is expected to return a dependency, typically the class of
    the implementation when defined as a service. You may also use a factory dependency.

    The function will not be wired, you'll need to do it yourself if you need it.

    .. doctest:: helpers_implementation

        >>> from antidote import implementation, Service, factory, world
        >>> class Interface:
        ...     pass
        >>> class A(Interface, Service):
        ...     pass
        >>> class B(Interface):
        ...     pass
        >>> @factory
        ... def build_b() -> B:
        ...     return B()
        >>> @implementation(Interface, dependencies=['choice'])
        ... def choose_interface(choice: str):
        ...     if choice == 'a':
        ...         return A  # One could also use A.with_kwargs(...)
        ...     else:
        ...         return B @ build_b  # or B @ build_b.with_kwargs(...)
        >>> world.singletons.add('choice', 'b')
        >>> world.get(Interface)
        <B ...>
        >>> # Changing choice doesn't matter anymore as the implementation is permanent.
        ... with world.test.clone(overridable=True):
        ...     world.singletons.add('choice', 'a')
        ...     world.get(Interface)
        <B ...>

    Args:
        interface: Interface for which an implementation will be provided
        permanent: Whether the function should be called each time the interface is needed
            or not. Defaults to :py:obj:`True`.
        auto_wire: Whether the function should have its arguments injected or not
            with :py:func:`~.injection.inject`.
        dependencies: Propagated to :py:func:`~.injection.inject`.
        use_names: Propagated to :py:func:`~.injection.inject`.
        use_type_hints: Propagated to :py:func:`~.injection.inject`.

    Returns:
        The decorated function, unmodified.
    """
    if not inspect.isclass(interface):
        raise TypeError(f"interface must be a class, not a {type(interface)}")

    if not (auto_wire is None or isinstance(auto_wire, bool)):
        raise TypeError(f"auto_wire can be None or a boolean, not {type(auto_wire)}")

    @inject
    def register(func, indirect_provider: IndirectProvider):
        from ._providers.factory import FactoryDependency
        from ._providers.service import Build

        if inspect.isfunction(func):
            if auto_wire:
                func = inject(func,
                              dependencies=dependencies,
                              use_names=use_names,
                              use_type_hints=use_type_hints)

            @functools.wraps(func)
            def linker():
                dependency = func()
                cls = dependency
                if isinstance(cls, Build):
                    cls = cls.dependency
                if isinstance(cls, FactoryDependency):
                    cls = cls.dependency

                if not (isinstance(cls, type) and inspect.isclass(cls)
                        and issubclass(cls, interface)):
                    raise TypeError(f"{func} is expected to return a class or a "
                                    f"Service / Factory dependency which implements"
                                    f"{interface}")
                return dependency

            indirect_provider.register_link(interface, linker=linker, permanent=permanent)
        else:
            raise TypeError(f"implementation must be applied on a function, "
                            f"not a {type(func)}")
        return func

    return register
