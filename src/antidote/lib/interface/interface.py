from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    cast,
    Generic,
    Mapping,
    Optional,
    overload,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from typing_extensions import final, get_args, get_origin, Literal, ParamSpec, Protocol, TypeGuard

from ... import Wiring
from ..._internal import API, Default, retrieve_or_validate_injection_locals
from ...core import Catalog, Dependency, TypeHintsLocals, world
from ..lazy import LazyFunction, LazyMethod
from ._interface import ImplementsImpl
from ._internal import create_constraints, ImplementationQuery
from .predicate import NeutralWeight, Predicate, PredicateConstraint, PredicateWeight

__all__ = [
    "implements",
    "instanceOf",
    "Overridable",
    "Interface",
    "LazyInterface",
    "is_interface",
]

C = TypeVar("C", bound=type)
T = TypeVar("T")
Itf = TypeVar("Itf", contravariant=True)
F = TypeVar("F", bound=Callable[..., Any])
Weight = TypeVar("Weight", bound=PredicateWeight)
Out = TypeVar("Out", covariant=True)
P = ParamSpec("P")


@API.public
class Interface(Protocol):
    """
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
        >>> world.instance[Service].all()
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
        >>> world.instance[Command].all(qualified_by=V1)
        [<WindowsCommand ...>, <LinuxCommand ...>]

    Antidote also provides more complex ways to select specific qualifiers such as:

    .. doctest:: lib_interface_decorator_qualified_by

        >>> world.instance[Command].all(qualified_by_one_of=[System.WINDOWS, System.LINUX])
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
        __obj: **/positional-only/** Interface class which implementations should implement.
            Implementations should be a subclass of it. The interface can also be a
            :py:class:`~typing.Protocol` in which case type checking will only be enforced if
            :py:func:`~typing.runtime_checkable` is used.

    Returns:
        decorated interface class.

    """

    @overload
    def __call__(self, __obj: C, *, catalog: Catalog = ...) -> C:
        ...

    @overload
    def __call__(
        self,
        __obj: Callable[P, T],
        *,
        catalog: Catalog = ...,
    ) -> FunctionInterface[P, T]:
        ...

    @overload
    def __call__(self, *, catalog: Catalog = ...) -> InterfaceDecorator:
        ...

    def __call__(
        self,
        __obj: object = None,
        *,
        catalog: Catalog = world,
    ) -> object:
        ...

    @overload
    def lazy(self, *, catalog: Catalog = world) -> InterfaceLazyDecorator:
        ...

    @overload
    def lazy(
        self,
        __func: LazyFunction[P, T],
        *,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def lazy(
        self,
        __func: Callable[P, T],
        *,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    def lazy(
        self,
        __func: object = None,
        *,
        catalog: Catalog = world,
    ) -> object:
        ...


@API.public
class Overridable(Protocol):
    """ """

    @overload
    def __call__(
        self,
        __obj: C,
        *,
        wiring: Wiring | None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> C:
        ...

    @overload
    def __call__(
        self,
        __obj: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> FunctionInterface[P, T]:
        ...

    @overload
    def __call__(
        self,
        *,
        inject: None = ...,
        wiring: Wiring | None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> InterfaceDecorator:
        ...

    def __call__(
        self,
        __obj: object = None,
        *,
        inject: None | Default = Default.sentinel,
        wiring: Wiring | None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        ...

    @overload
    def lazy(
        self,
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> OverridableLazyDecorator:
        ...

    @overload
    def lazy(
        self,
        __func: staticmethod[LazyFunction[P, T]],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def lazy(
        self,
        __func: LazyMethod[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def lazy(
        self,
        __func: LazyFunction[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def lazy(
        self,
        __func: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    def lazy(
        self,
        __func: object = None,
        *,
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        ...


@API.public
class FunctionInterface(Protocol[P, Out]):
    @property
    def __wrapped__(self) -> Callable[P, Out]:
        ...

    def __antidote_dependency_hint__(self) -> Callable[P, Out]:  # for Mypy
        ...

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Dependency[Callable[P, Out]]:
        ...

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Dependency[Sequence[Callable[P, Out]]]:
        ...


@API.public
class LazyInterface(Protocol[P, Out]):
    # Have to copy-paste LazyFunction for Mypy... error: ParamSpec "P" is unbound
    @property
    def __wrapped__(self) -> Callable[P, Out]:
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Callable[P, Dependency[Out]]:
        ...

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Callable[P, Dependency[Sequence[Out]]]:
        ...


@API.public
@final
@dataclass
class instanceOf(Generic[T]):
    """
    .. versionadded:: 1.2

    Used to construct the actual dependency for the provider handling the interfaces.

    .. doctest:: lib_interface_implementations_of

        >>> from antidote import interface, implements, inject, world, instanceOf
        >>> @interface
        ... class Service:
        ...     pass
        >>> @implements(Service)
        ... class ServiceImpl(Service):
        ...     pass
        >>> world.get[Service].single()
        <ServiceImpl ...>
        >>> # the former is equivalent to:
        ... world.get(instanceOf(Service).single())
        <ServiceImpl ...>

    """

    __slots__ = ("__explicit_interface", "__dict__")
    __explicit_interface: Type[T] | None

    def __antidote_dependency_hint__(self) -> T:
        if self.__explicit_interface is not None:
            return cast(T, self.__explicit_interface)
        cls = get_args(cast(Any, self).__orig_class__)[0]
        return cast(T, get_origin(cls) or cls)

    def __init__(self, __interface: Type[T] | None = None) -> None:
        """
        Args:
            __interface: **/positional-only/** Interface for which implementations should be
                retrieved. It must have been decorated with :py:func:`~.interface`.
        """
        # Support generic interfaces
        __interface = cast(Type[T], get_origin(__interface) or __interface)
        if not (__interface is None or isinstance(__interface, type)):
            raise TypeError(f"interface must be a class if specified, got a {type(__interface)!r}")
        object.__setattr__(self, f"_{type(self).__name__}__explicit_interface", __interface)

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
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

        return ImplementationQuery[T](
            interface=self.__antidote_dependency_hint__(),
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
        )

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Dependency[Sequence[T]]:
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
        from ._internal import create_constraints

        return ImplementationQuery[Sequence[T]](
            interface=self.__antidote_dependency_hint__(),
            constraints=create_constraints(
                *constraints, qualified_by=qualified_by, qualified_by_one_of=qualified_by_one_of
            ),
            all=True,
        )


@API.public
class implements:
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

    class protocol(Generic[Itf]):
        """
        See :py:class:`.ClassImplements` for the actual documentation. This class only serves as
        a placeholder for proper typing by mypy.
        """

        def __init__(
            self,
            *,
            wiring: Wiring | None | Default = Default.sentinel,
            type_hints_locals: Union[
                Mapping[str, object], Literal["auto"], Default, None
            ] = Default.sentinel,
            catalog: Catalog = world,
        ) -> None:
            ...

        def __call__(self, __impl: C) -> C:
            ...

        def when(
            self,
            *conditions: Predicate[Weight | NeutralWeight]
            | Optional[Weight | NeutralWeight]
            | bool,
            qualified_by: Optional[object | list[object]] = None,
        ) -> Callable[[C], C]:
            ...

        def overriding(self, __existing_implementation: Itf) -> Callable[[C], C]:
            ...

        def by_default(self, __impl: C) -> C:
            ...

    def __call__(self, __impl: Any) -> Any:
        ...

    def when(
        self,
        *conditions: Predicate[Weight]
        | Predicate[NeutralWeight]
        | Weight
        | NeutralWeight
        | None
        | bool,
        qualified_by: Optional[object | list[object]] = None,
    ) -> Callable[[Any], Any]:
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
        ...

    def overriding(self, __existing_implementation: Any) -> Callable[[Any], Any]:
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
        ...

    def by_default(self, __impl: Any) -> Any:
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
            __impl: **/positional-only/** default implementation for the interface.

        Returns:
            decorated class
        """
        ...

    @classmethod
    def lazy(
        cls,
        __interface: LazyInterface[P, T],
        *,
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
    ) -> LazyImplements[P, T]:
        instance = ImplementsImpl(
            interface=__interface,
            type_hints_locals=retrieve_or_validate_injection_locals(type_hints_locals),
            inject=inject,
            _lazy=True,
        )
        return instance  # type: ignore

    @overload
    def __new__(
        cls,
        __interface: Type[T],
        *,
        wiring: Wiring | None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> ClassImplements[Type[T]]:
        ...

    @overload
    def __new__(
        cls,
        __interface: FunctionInterface[P, T],
        *,
        inject: None | Default = ...,
        type_hints_locals: TypeHintsLocals = ...,
    ) -> FunctionImplements[Callable[P, T]]:
        ...

    def __new__(
        cls,
        __interface: Any,
        *,
        inject: None | Default = Default.sentinel,
        wiring: Wiring | None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog | Default = Default.sentinel,
    ) -> implements:
        instance: object = ImplementsImpl(
            interface=__interface,
            type_hints_locals=retrieve_or_validate_injection_locals(type_hints_locals),
            catalog=catalog,
            inject=inject,
            wiring=wiring,
        )
        return instance  # type: ignore


setattr(implements, "protocol", ImplementsImpl)


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class InterfaceDecorator(Protocol):
    @overload
    def __call__(self, __obj: C) -> C:
        ...

    @overload
    def __call__(self, __obj: Callable[P, T]) -> FunctionInterface[P, T]:
        ...

    def __call__(self, __obj: object) -> object:
        ...


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class InterfaceLazyDecorator(Protocol):
    @overload
    def __call__(self, __obj: LazyFunction[P, T]) -> LazyInterface[P, T]:
        ...

    @overload
    def __call__(self, __obj: Callable[P, T]) -> LazyInterface[P, T]:
        ...

    def __call__(self, __obj: object) -> object:
        ...


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class OverridableLazyDecorator(Protocol):
    @overload
    def __call__(self, __obj: classmethod[LazyFunction[P, T]]) -> LazyInterface[P, T]:
        ...

    @overload
    def __call__(self, __obj: staticmethod[LazyFunction[P, T]]) -> LazyInterface[P, T]:
        ...

    @overload
    def __call__(self, __obj: LazyMethod[P, T]) -> LazyInterface[P, T]:
        ...

    @overload
    def __call__(self, __obj: LazyFunction[P, T]) -> LazyInterface[P, T]:
        ...

    @overload
    def __call__(self, __obj: Callable[P, T]) -> LazyInterface[P, T]:
        ...

    def __call__(self, __obj: object) -> object:
        ...


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class ClassImplements(implements, Generic[Itf], ABC):
    def __call__(self, __impl: C) -> C:
        ...

    def when(
        self,
        *conditions: Predicate[Weight]
        | Predicate[NeutralWeight]
        | Weight
        | NeutralWeight
        | None
        | bool,
        qualified_by: Optional[object | list[object]] = None,
    ) -> Callable[[C], C]:
        ...

    def overriding(self, __existing_implementation: Itf) -> Callable[[C], C]:
        ...

    def by_default(self, __impl: C) -> C:
        ...


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class LazyImplementsDecorator(Protocol[P, T]):
    @overload
    def __call__(self, __impl: LazyMethod[P, T]) -> LazyMethod[P, T]:
        ...

    @overload
    def __call__(self, __impl: LazyFunction[P, T]) -> LazyFunction[P, T]:
        ...

    @overload
    def __call__(
        self, __impl: staticmethod[LazyFunction[P, T]]
    ) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(self, __impl: staticmethod[Callable[P, T]]) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(self, __impl: Callable[P, T]) -> LazyFunction[P, T]:
        ...

    def __call__(self, __impl: object) -> object:
        ...


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class LazyImplements(Protocol[P, T]):
    by_default: LazyImplementsDecorator[P, T]

    # FIXME: Mypy complains again about unbound ParamSpec 'P'...
    @overload
    def __call__(self, __impl: LazyMethod[P, T]) -> LazyMethod[P, T]:
        ...

    @overload
    def __call__(self, __impl: LazyFunction[P, T]) -> LazyFunction[P, T]:
        ...

    @overload
    def __call__(
        self, __impl: staticmethod[LazyFunction[P, T]]
    ) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(self, __impl: staticmethod[Callable[P, T]]) -> staticmethod[LazyFunction[P, T]]:
        ...

    @overload
    def __call__(self, __impl: Callable[P, T]) -> LazyFunction[P, T]:
        ...

    def __call__(self, __impl: object) -> object:
        ...

    def when(
        self,
        *conditions: Predicate[Weight]
        | Predicate[NeutralWeight]
        | Weight
        | NeutralWeight
        | None
        | bool,
        qualified_by: Optional[object | list[object]] = None,
    ) -> LazyImplementsDecorator[P, T]:
        ...

    def overriding(
        self,
        __existing_implementation: LazyFunction[P, T]
        | LazyMethod[P, T]
        | staticmethod[LazyFunction[P, T]],
    ) -> LazyImplementsDecorator[P, T]:
        ...


# Used for typing purposes, the protocol itself is not part of the public API.
@API.private
class FunctionImplements(implements, Generic[T], ABC):
    def __call__(self, __impl: T) -> T:
        ...

    def when(
        self,
        *conditions: Predicate[Weight]
        | Predicate[NeutralWeight]
        | Weight
        | NeutralWeight
        | None
        | bool,
        qualified_by: Optional[object | list[object]] = None,
    ) -> Callable[[T], T]:
        ...

    def overriding(self, __existing_implementation: T) -> Callable[[T], T]:
        ...

    def by_default(self, __impl: T) -> T:
        ...


@API.public
def is_interface(__obj: object) -> TypeGuard[FunctionInterface[Any, Any] | LazyInterface[Any, Any]]:
    from ._function import InterfaceWrapper

    return isinstance(__obj, InterfaceWrapper)
