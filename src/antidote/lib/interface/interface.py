from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast, Generic, List, Mapping, Optional, Type, TypeVar, Union

from typing_extensions import final, get_origin, Literal

from ._internal import (
    create_constraints,
    override_implementation,
    register_default_implementation,
    register_implementation,
    register_interface,
)
from ._provider import InterfaceProvider
from ._query import Query
from .predicate import NeutralWeight, Predicate, PredicateConstraint, PredicateWeight
from .qualifier import QualifiedBy
from ..._internal import API
from ..._internal.localns import retrieve_or_validate_injection_locals
from ..._internal.utils import Default
from ...core import Dependency, inject

__all__ = ["interface", "implements", "ImplementationsOf"]

Itf = TypeVar("Itf", bound=type)
C = TypeVar("C", bound=type)
T = TypeVar("T")
Weight = TypeVar("Weight", bound=PredicateWeight)


@API.public
def interface(klass: C) -> C:
    """
    .. versionadded:: 1.2

    Declares a class as an interface. One or multiple implementations can then be declared for it:

    .. doctest:: lib_interface_decorator

        >>> from antidote import interface, implements, inject, world
        >>> @interface
        ... class Service:
        ...     pass
        >>> @implements(Service)
        ... class ServiceImpl(Service):
        ...     pass
        >>> @inject
        ... def f(service: Service = inject.me()) -> Service:
        ...     return service
        >>> f()
        <ServiceImpl ...>
        >>> world.get[Service].single()
        <ServiceImpl ...>
        >>> world.get(Service)  # equivalent to previous line
        <ServiceImpl ...>


    Alternative implementations can be declared and one can retrieve all of them at once:

    .. doctest:: lib_interface_decorator

        >>> @implements(Service)
        ... class ServiceImplV2(Service):
        ...     pass
        >>> @inject
        ... def f(services: list[Service] = inject.me()) -> list[Service]:
        ...     return services
        >>> f()
        [<ServiceImplV2 ...>, <ServiceImpl ...>]
        >>> world.get[Service].all()
        [<ServiceImplV2 ...>, <ServiceImpl ...>]

    However, as defined Antidote is not able to provide a single implementation anymore.

    .. doctest:: lib_interface_decorator

        >>> world.get[Service].single()
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        DependencyInstantiationError: ...

    To enable Antidote to select one implementation among many, you need to use
    :py:class:`.Predicate` and eventually
    :py:class:`.PredicateConstraint`. Antidote currently only provides one kind out
    of the box :py:class:`.QualifiedBy`.

    Qualifiers can be used to narrow the candidate implementations for an interface. Qualifiers are
    matched by their :py:func:`id` and not their equality.

    .. doctest:: lib_interface_decorator_qualified_by

        >>> from enum import Enum, auto
        >>> from antidote import interface, implements, inject, world
        >>> class System(Enum):
        ...     LINUX = auto()
        ...     WINDOWS = auto()
        >>> V1 = object()
        >>> @interface
        ... class Command:
        ...     def execute(self) -> str:
        ...         raise NotImplementedError()
        >>> @implements(Command).when(qualified_by=[System.LINUX, V1])
        ... class LinuxCommand(Command):
        ...     def execute(self) -> str:
        ...         return "Linux"
        >>> @implements(Command).when(qualified_by=[System.WINDOWS, V1])
        ... class WindowsCommand(Command):
        ...     def execute(self) -> str:
        ...         return "Windows"
        >>> @inject
        ... def run_command(command: Command = inject.me(qualified_by=System.LINUX)) -> str:
        ...     return command.execute()
        >>> run_command()
        'Linux'
        >>> world.get[Command].all(qualified_by=V1)
        [<WindowsCommand ...>, <LinuxCommand ...>]

    Antidote also provides more complex ways to select specific qualifiers such as:

    .. doctest:: lib_interface_decorator_qualified_by

        >>> world.get[Command].all(qualified_by_one_of=[System.WINDOWS, System.LINUX])
        [<WindowsCommand ...>, <LinuxCommand ...>]

    .. tip::

        For Python ealier than 3.9, before PEP614, you can rely on the following trick for
        decorators:

        .. doctest:: lib_interface_decorator_qualified_by

            >>> from typing import TypeVar
            >>> T = TypeVar('T')
            >>> def _(x: T) -> T:
            ...     return x
            >>> @_(implements(Command).when(qualified_by=[System.LINUX, V1]))
            ... class LinuxCommand(Command):
            ...     def execute(self) -> str:
            ...         return "Linux"



    Args:
        klass: **/positional-only/** Interface class which implementations should implement.
            Implementations should be a subclass of it. The interface can also be a
            :py:class:`~typing.Protocol` in which case type checking will only be enforced if
            :py:func:`~typing.runtime_checkable` is used.

    Returns:
        decorated interface class.

    """
    if not isinstance(klass, type):
        raise TypeError(f"Expected a class for the interface, got a {type(klass)!r}")
    register_interface(klass)
    return klass


@API.public
@final
class implements(Generic[Itf]):
    """
    .. versionadded:: 1.2

    Declares the decorated class to be a candidate implementation for the specified interface.
    The interface can also be a :py:class:`~typing.Protocol`. If the interface is a regular class
    or a :py:func:`~typing.runtime_checkable` Protocol, the implementation will be type checked.

    .. doctest:: lib_interface_implements

        >>> from antidote import interface, implements, inject, world
        >>> @interface
        ... class Service:
        ...     pass
        >>> @implements(Service)
        ... class ServiceImpl(Service):
        ...     pass
        >>> @implements(Service)
        ... class BadImpl:
        ...     pass
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        TypeError: ...

    """

    def __init__(
        self,
        __interface: Itf,
        *,
        type_hints_locals: Union[
            Mapping[str, object], Literal["auto"], Default, None
        ] = Default.sentinel,
    ) -> None:
        """
        Args:
            __interface: **/positional-only/** Interface class.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. When :code:`ignore_type_hints` is
                :py:obj:`True`, this features cannot be used. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.

                .. versionadded:: 1.3
        """
        self.__interface = __interface
        self.__type_hints_locals = retrieve_or_validate_injection_locals(type_hints_locals)

    def __call__(self, klass: C) -> C:
        register_implementation(
            interface=self.__interface,
            implementation=klass,
            type_hints_locals=self.__type_hints_locals,
            predicates=[],
        )
        return klass

    def when(
        self,
        *_predicates: Predicate[Weight] | Predicate[NeutralWeight],
        qualified_by: Optional[object | list[object]] = None,
    ) -> Callable[[C], C]:
        """
        Associate :py:class:`.Predicate` with the decorated implementation. The
        implementation will only be used if all the predicates return a weight. In case multiple
        implementations are valid candidates, their ordering is determined by the total weight of
        all predicates.

        .. note::

            See :py:func:`~.interface` for examples.

        Args:
            *_predicates: Objects implementing the :py:class:`.Predicate` protocol.
            qualified_by: An object, or a list of it, by which the implementation is qualified.
                Those qualifiers can then be used at runtime to narrow the possible implementations
                for an interface. Beware, qualifiers rely on the :py:func:`id` of the objects, not
                their equality.

        Returns:
            class decorator

        """
        predicates: list[Predicate[Weight] | Predicate[NeutralWeight]] = list(_predicates)
        if qualified_by is not None:
            if isinstance(qualified_by, list):
                predicates.append(QualifiedBy(*cast(List[object], qualified_by)))
            else:
                predicates.append(QualifiedBy(qualified_by))

        def register(__klass: C) -> C:
            register_implementation(
                interface=self.__interface,
                implementation=__klass,
                type_hints_locals=self.__type_hints_locals,
                predicates=predicates,
            )
            return __klass

        return register

    def overriding(self, __existing_implementation: Itf) -> Callable[[C], C]:
        """
        .. versionadded: 1.4

        Override an existing implementation with the same predicates, so in the same conditions as
        the existing one.

        .. doctest:: lib_interface_implements_overriding

            >>> from antidote import interface, implements, world
            >>> @interface
            ... class Base:
            ...     pass
            >>> @implements(Base)
            ... class BaseImpl(Base):
            ...     pass
            >>> world.get[Base].single()
            <BaseImpl object at ...>
            >>> @implements(Base).overriding(BaseImpl)
            ... class Custom(Base):
            ...     pass
            >>> world.get[Base].single()
            <Custom object at ...>

        Trying to override again the same implementation will raise an error:

        .. doctest:: lib_interface_implements_overriding

            >>> @implements(Base).overriding(BaseImpl)
            ... class CustomV2(Base):
            ...     pass
            Traceback (most recent call last):
              File "<stdin>", line 1, in ?
            RuntimeError

        Args:
            __existing_implementation: **/positional-only/** Existing implementation to override.

        Returns:
            class decorator

        """
        if not isinstance(__existing_implementation, type):
            raise TypeError(
                f"Expected a class for the overridden implementation, "
                f"got a {type(__existing_implementation)!r}"
            )

        def register(__klass: C) -> C:
            override_implementation(
                interface=self.__interface,
                existing_implementation=__existing_implementation,
                new_implementation=__klass,
                type_hints_locals=self.__type_hints_locals,
            )
            return __klass

        return register

    def by_default(self, __klass: C) -> C:
        """
        .. versionadded: 1.4

        Define a default implementation used when no alternative was found. It can also
        be overridden with :py:meth:`~.implements.overriding`.

        .. doctest:: lib_interface_implements_by_default

            >>> from antidote import interface, implements, world
            >>> @interface
            ... class Base:
            ...     pass
            >>> @implements(Base).by_default
            ... class Default(Base):
            ...     pass
            >>> world.get[Base].single()
            <Default object at ...>
            >>> @implements(Base)
            ... class BaseImpl(Base):
            ...     pass
            >>> world.get[Base].single()
            <BaseImpl object at ...>

        Args:
            __klass: **/positional-only/** default implementation for the interface.

        Returns:
            decorated class
        """
        register_default_implementation(
            interface=self.__interface,
            implementation=__klass,
            type_hints_locals=self.__type_hints_locals,
        )
        return __klass


@API.public
@final
@dataclass(frozen=True, init=False)
class ImplementationsOf(Generic[T]):
    """
    .. versionadded:: 1.2

    Used to construct the actual dependency for the provider handling the interfaces.

    .. doctest:: lib_interface_implementations_of

        >>> from antidote import interface, implements, inject, world, ImplementationsOf
        >>> @interface
        ... class Service:
        ...     pass
        >>> @implements(Service)
        ... class ServiceImpl(Service):
        ...     pass
        >>> world.get[Service].single()
        <ServiceImpl ...>
        >>> # the former is equivalent to:
        ... world.get(ImplementationsOf(Service).single())
        <ServiceImpl ...>

    """

    __slots__ = ("__interface",)
    __interface: Type[T]

    @inject
    def __init__(
        self, interface: Type[T], *, provider: InterfaceProvider = inject.get(InterfaceProvider)
    ) -> None:
        """
        Args:
            interface: **/positional-only/** Interface for which implementations should be
                retrieved. It must have been decorated with :py:func:`~.interface`.
        """
        # Support generic interfaces
        interface = cast(Type[T], get_origin(interface) or interface)
        if not isinstance(interface, type):
            raise TypeError(f"Expected a class, got a {type(interface)!r}")
        if not provider.has_interface(interface):
            raise ValueError(f"Interface {interface!r} was not decorated with @interface.")
        object.__setattr__(self, f"_{type(self).__name__}__interface", interface)

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object]] = None,
        qualified_by_one_of: Optional[list[object]] = None,
    ) -> Dependency[list[T]]:
        """
        Construct the dependency to retrieve all implementations matching given constraints for
        the specified interface. Having no implementation matching the constraints will not raise
        an error, but instead an empty list will be retrieved.

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.

        Returns:
            A dependency for the list of implementations matching the constraints.
        """
        query = Query(
            interface=self.__interface,
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
            all=True,
        )
        return cast(Dependency[List[T]], query)

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object]] = None,
        qualified_by_one_of: Optional[list[object]] = None,
    ) -> Dependency[T]:
        """
        Construct the dependency to retrieve a single implementation matching given constraints for
        the specified interface. If multiple or no implementation is found, an error will be raised
        upon retrieval.

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.

        Returns:
            A dependency for the list of implementations matching the constraints.
        """
        query = Query(
            interface=self.__interface,
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
            all=False,
        )
        return cast(Dependency[T], query)
