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

from ..._internal import API, Default, retrieve_or_validate_injection_locals
from ..._internal.typing import C, In, Out, T
from ...core import AntidoteError, Catalog, Dependency, TypeHintsLocals, Wiring, world
from ..lazy_ext import antidote_lib_lazy, LazyFunction, LazyMethod
from ._interface import ImplementsImpl, InterfaceImpl
from ._internal import create_constraints, ImplementationQuery
from .predicate import (
    HeterogeneousWeightError,
    ImplementationWeight,
    MergeablePredicate,
    MergeablePredicateConstraint,
    NeutralWeight,
    Predicate,
    PredicateConstraint,
)
from .qualifier import QualifiedBy

__all__ = [
    "AmbiguousImplementationChoiceError",
    "HeterogeneousWeightError",
    "SingleImplementationNotFoundError",
    "ImplementationWeight",
    "MergeablePredicate",
    "MergeablePredicateConstraint",
    "NeutralWeight",
    "Predicate",
    "Interface",
    "InterfaceLazy",
    "PredicateConstraint",
    "QualifiedBy",
    "implements",
    "instanceOf",
    "interface",
    "antidote_lib_interface",
    "is_interface",
]

P = ParamSpec("P")
Weight = TypeVar("Weight", bound=ImplementationWeight)

interface: Interface = InterfaceImpl()


@API.public
def antidote_lib_interface(catalog: Catalog) -> None:
    """
    Adds the necessary for the use of :py:obj:`.interface` into the specified catalog. The function
    is idempotent, and will not raise an error if it was already applied

    .. doctest:: lib_interface_extension_include

        >>> from antidote import new_catalog, antidote_lib_interface
        >>> # Include at catalog creation
        ... catalog = new_catalog(include=[antidote_lib_interface])
        >>> # Or afterwards
        ... catalog.include(antidote_lib_interface)

    """
    from ..injectable_ext import antidote_lib_injectable
    from ._provider import InterfaceProvider

    if InterfaceProvider not in catalog.providers:
        catalog.include(InterfaceProvider)
    catalog.include(antidote_lib_injectable)
    catalog.include(antidote_lib_lazy)


@API.public
def is_interface(__obj: object) -> TypeGuard[FunctionInterface[Any, Any] | LazyInterface[Any, Any]]:
    """
    Returns :py:obj:`True` if the given object is a :py:class:`.FunctionInterface` or a
    :py:class:`.LazyInterface`.

    .. doctest:: lib_interface_is_interface

        >>> from antidote import interface, is_interface
        >>> @interface
        ... def f() -> None:
        ...     pass
        >>> is_interface(f)
        True
        >>> is_interface(object())
        False

    """
    from ._function import InterfaceWrapper

    return isinstance(__obj, InterfaceWrapper)


@API.public
class AmbiguousImplementationChoiceError(AntidoteError):
    """
    Raised when at least two implementations matches the specified constraints and have the same
    weight.
    """

    @API.private
    def __init__(self, *, query: object, a: object, b: object) -> None:
        super().__init__(
            f"At least two implementations match {query!r}. Consider using more specific predicate "
            f"constraints or different weight values. Found: {a!r} and {b!r}"
        )


@API.public
class SingleImplementationNotFoundError(AntidoteError):
    """
    Raised when no implementation matched a query for a single implementation
    """

    @API.private
    def __init__(self, *, query: object) -> None:
        super().__init__(f"No single implementation could match {query!r}.")


@API.public
class Interface(Protocol):
    """
    Use the :py:obj:`.interface` singleton object.

    Declares an interface contract for which one or multiple implementations can be registered
    through :py:class:`.implements`. The interface can be a class/protocol, a function or a
    :py:obj:`.lazy` call. Implementations won't be directly accessible unless explicitly defined
    as such.

    A. For a class, :py:class:`.implements` ensures that all implementations are subclasses of it.
       A single implementation can be retrieved directly with the interface class as a dependency.
       For additional functionnality use :py:class:`.instanceOf`.

        .. doctest:: lib_interface_decorator

            >>> from antidote import interface, implements, inject, world, instanceOf
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
            >>> world[Service]
            <ServiceImpl ...>
            >>> world[instanceOf(Service)]
            <ServiceImpl ...>
            >>> world[instanceOf(Service).single()]
            <ServiceImpl ...>

    B. With a :py:class:`~typing.Protocol` implementations are only checked if decorated with
       :py:func:`~typing.runtime_checkable`. While a Protocol can be used with the same syntax
       as before, it will generate static typing errors with :py:class:`~typing.Type`. So an
       alternative syntax exists:

        .. doctest:: lib_interface_decorator

            >>> from typing import Protocol
            >>> @interface
            ... class IService(Protocol):
            ...     pass
            >>> @implements.protocol[IService]()
            ... class MyService:
            ...     pass
            >>> world[instanceOf[IService]]
            <MyService ...>
            >>> world[instanceOf[IService]().single()]
            <MyService ...>

    C. A function can also be declared as an interface acting as protocol. :py:class:`.implements`
       ensures that the implementation signature matches the interface one.

        .. doctest:: lib_interface_decorator

            >>> from typing import Callable
            >>> @interface
            ... def callback(x: int) -> str:
            ...     ...
            >>> @implements(callback)
            ... def callback_impl(x: int) -> str:
            ...     return str(x)
            >>> world[callback]
            <function callback_impl ...>
            >>> world[callback.single()]
            <function callback_impl ...>
            >>> @inject
            ... def f(callback: Callable[[int], str] = inject[callback]) -> Callable[[int], str]:
            ...     return callback
            >>> f()
            <function callback_impl ...>

    D. Finally a lazy dependency can also be an interface. Similarly to a function interface, a
       matching signature is enforced.

        .. doctest:: lib_interface_decorator

            >>> from typing import Callable
            >>> @interface.lazy
            ... def template(name: str) -> str:
            ...     ...
            >>> @implements.lazy(template)
            ... def hello_template(name: str) -> str:
            ...     return f"Hello {name}"
            >>> world[template("John")]
            'Hello John'
            >>> world[template.single()(name="John")]
            'Hello John'
            >>> @inject
            ... def f(out: str = inject[template("John")]) -> str:
            ...     return out
            >>> f()
            'Hello John'

    An interface can also have multiple implementations and all of them be retrieved with
    :py:meth:`.instanceOf.all` for a class, :py:meth:`.FunctionInterface.all` for a function
    and :py:meth:`.LazyInterface.all` for :py:obj:`.lazy` call:

    .. doctest:: lib_interface_decorator_2

        >>> from antidote import interface, implements, world, instanceOf
        >>> @interface
        ... class Service:
        ...     pass
        >>> @implements(Service)
        ... class ServiceImpl(Service):
        ...     pass
        >>> @implements(Service)
        ... class ServiceImpl2(Service):
        ...     pass
        >>> world[instanceOf(Service).all()]
        [<ServiceImpl2 object ...>, <ServiceImpl object ...>]
        >>> world[Service]
        Traceback (most recent call last):
          File "<stdin>", line 1, in ?
        AmbiguousImplementationChoiceError: ...

    Selecting a single implementation is not possible anymore as is though. For this three different
    mechanisms exist to select one or multiple implementations among many:

    1. conditions with :py:meth:`.implements.when`, defnining whehter an implementation is
       registered or not.

        .. doctest:: lib_interface_decorator_2a

            >>> from antidote import const, inject, interface, implements, world
            >>> CLOUD = const('AWS')  # some configuration loader somewhere
            >>> @inject
            ... def on_cloud(expected: str, actual: str = inject[CLOUD]) -> bool:
            ...     return expected == actual
            >>> @interface
            ... class CloudAPI:
            ...     pass
            >>> @implements(CloudAPI).when(on_cloud('GCP'))
            ... class GCPapi(CloudAPI):
            ...     pass
            >>> @implements(CloudAPI).when(on_cloud('AWS'))
            ... class AWSapi(CloudAPI):
            ...     pass
            >>> world[CloudAPI]
            <AWSapi object ...>

    2. At request, constraints be used to filter out implementations. In the following example
       we're using qualifiers which are provided out of the box. But you may also define your
       own :py:class:`.Predicate` and :py:class:`.PredicateConstraint` to customize this. The
       :code:`qualified_by` parameters are actually implemented through :py:class:`.QualifiedBy`
       underneath.

        .. doctest:: lib_interface_decorator_2b

            >>> from antidote import const, inject, interface, implements, world, instanceOf
            >>> @interface
            ... class CloudAPI:
            ...     pass
            >>> @implements(CloudAPI).when(qualified_by='GCP')
            ... class GCPapi(CloudAPI):
            ...     pass
            >>> @implements(CloudAPI).when(qualified_by='AWS')
            ... class AWSapi(CloudAPI):
            ...     pass
            >>> world[instanceOf(CloudAPI).single(qualified_by='GCP')]
            <GCPapi object ...>

    3. A tie between matching implementations can also be resolved through a different weight.
       For the sake of simplicity, it must be defined at declaration time. Out of the box, only
       :py:class:`.NeutralWeight` is used by Antidote, which as the name implies is always the
       same. To define your own weight system, see :py:class:`.ImplementationWeight`.

    It is also possible to define a default implementation which is used whenever no alternative
    implementation can. You can either define it to be the interface itself with
    :py:meth:`.Interface.as_default` or :py:meth:`.implements.as_default`:

    .. doctest:: lib_interface_decorator_4

        >>> from antidote import interface, implements
        >>> @interface.as_default
        ... class Service:
        ...     pass
        >>> world[Service]
        <Service object ...>
        >>> @implements(Service)
        ... class ServiceImpl(Service):
        ...     pass
        >>> world[Service]
        <ServiceImpl object ...>
        >>> # For a lazy call
        ... @interface.lazy.as_default
        ... def template(name: str) -> str:
        ...     return f"Default {name}"
        >>> world[template(name='x')]
        'Default x'

    Any implementation, default included, can be overridden as long as the catalog is not frozen
    with :py:meth:`.implements.overriding`.

    .. note::

        The registration of the interface is thread-safe.

    .. tip::

        For Python ealier than 3.9, before PEP614, you can rely on the following trick for
        decorators:

        .. doctest:: lib_interface_decorator

            >>> from typing import TypeVar
            >>> T = TypeVar('T')
            >>> def _(x: T) -> T:
            ...     return x
            >>> @_(implements(Service).when(qualified_by='yet another'))
            ... class YetAnotherServiceImpl(Service):
            ...     pass
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
        """
        Declares a class/protocol or a function interface. See :py:class:`.Interface` for an
        overview.

        Args:
            __obj: **/positional-only/** Interface contract which can be a class, protocol or a
                function.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            A :py:class:`.FunctionInterface` if a function interface, otherwise the original class.

        """
        ...

    @overload
    def as_default(
        self,
        __obj: C,
        *,
        wiring: Wiring | None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> C:
        ...

    @overload
    def as_default(
        self,
        __obj: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> FunctionInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        *,
        inject: None = ...,
        wiring: Wiring | None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = ...,
    ) -> InterfaceDecorator:
        ...

    def as_default(
        self,
        __obj: object = None,
        *,
        inject: None | Default = Default.sentinel,
        wiring: Wiring | None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        """
        Declares the decorated interface to also be its own default implementation. The latter is
        used if and only if there are no alternative implementations that can be provided.

        .. doctest:: lib_interface_interface_as_default

            >>> from antidote import interface, world, implements
            >>> @interface.as_default
            ... def validate(name: str) -> bool:
            ...     return len(name) < 10
            >>> world[validate]("very long name")
            False
            >>> # Default implementation also provided for all()
            ... len(world[validate.all()])
            1
            >>> # Add a "real" implementation
            ... @implements(validate)
            ... def custom_validate(name: str) -> bool:
            ...     return len(name) < 100
            >>> world[validate]("very long name")
            True
            >>> world[validate.all()] == [custom_validate]
            True
            >>> # As custom_validate isn't qualified by 'a' it cannot be provided. So the default
            ... # implementation is returned instead.
            ... world[validate.single(qualified_by='a')]("very long name")
            False

        You can customize more finely how the default implementation behaves by applying yourself
        either :py:obj:`.inject` or :py:obj:`.wire` or deactivate any injection by specifying
        :code:`inject` for a function or :code:`wiring` for a class to be py:obj:`None`.

        Args:
            __obj: **/positional-only/** Interface contract which can be a class or a function.
            inject: */Only a function interface/* Specifying :py:obj:`None` will prevent the use
                of py:obj:`.inject` on the function.
            wiring: */Only a class or protocol interface/* :py:class:`.Wiring` to be used on the
                class. By defaults will apply a simple :py:func:`.inject` on all methods. But it
                won't replace any :py:func:`.inject` that has been explicitly applied. Specifying
                :py:obj:`None` will prevent any wiring.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            A :py:class:`.FunctionInterface` if a function interface, otherwise the original class.

        """
        ...

    @property
    def lazy(self) -> InterfaceLazy:
        """
        Used to define :py:obj:`.lazy` call interface, see :py:class:`.InterfaceLazy`.
        """
        ...


@API.public
class InterfaceLazy(Protocol):
    @overload
    def __call__(self, *, catalog: Catalog = ...) -> InterfaceLazyDecorator:
        ...

    @overload
    def __call__(
        self,
        __func: LazyFunction[P, T],
        *,
        catalog: Catalog = ...,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def __call__(
        self,
        __func: Callable[P, T],
        *,
        catalog: Catalog = ...,
    ) -> LazyInterface[P, T]:
        ...

    def __call__(
        self,
        __func: object = None,
        *,
        catalog: Catalog = world,
    ) -> object:
        """
        Define a :py:obj:`.lazy` call interface. For more information on what an interface means,
        see :py:class:`.Interface`. To declare an implementation use :py:meth:`.implements.lazy`.

        .. doctest:: lib_interface_interface_lazy

            >>> from antidote import interface, implements, world, inject
            >>> @interface.lazy
            ... def template(name: str) -> str:
            ...     ...
            >>> @implements.lazy(template)
            ... def template_impl(name: str) -> str:
            ...     return f"My Template {name}"
            >>> world[template(name="World")]
            'My Template World'
            >>> @inject
            ... def f(world_template: str = inject[template(name="World")]) -> str:
            ...     return world_template
            >>> f()
            'My Template World'

        Args:
            __obj: **/positional-only/** Interface contract for a :py:obj:`.lazy` call.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            A :py:class:`.LazyInterface`.

        """
        ...

    @overload
    def as_default(
        self,
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> InterfaceLazyAsDefaultDecorator:
        ...

    @overload
    def as_default(
        self,
        __func: staticmethod[LazyFunction[P, T]],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        __func: LazyMethod[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        __func: LazyFunction[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    @overload
    def as_default(
        self,
        __func: Callable[P, T],
        *,
        inject: None = ...,
        type_hints_locals: TypeHintsLocals = ...,
        catalog: Catalog = world,
    ) -> LazyInterface[P, T]:
        ...

    def as_default(
        self,
        __func: object = None,
        *,
        inject: None | Default = Default.sentinel,
        type_hints_locals: TypeHintsLocals = Default.sentinel,
        catalog: Catalog = world,
    ) -> object:
        """
        Declares the decorated :py:obj:`.lazy` call interface to also be its own default
        implementation. The latter is used if and only if there are no alternative implementations
        that can be provided.

        .. doctest:: lib_interface_lazy_as_default

            >>> from antidote import interface, world, implements
            >>> @interface.lazy.as_default
            ... def template(name: str) -> str:
            ...     return f"Default {name}"
            >>> world[template(name="World")]
            'Default World'
            >>> # Default implementation also provided for all()
            ... world[template.all()(name="World")]
            ['Default World']
            >>> # Add a "real" implementation
            ... @implements.lazy(template)
            ... def custom_template(name: str) -> str:
            ...     return f"Custom {name}"
            >>> world[template(name="World")]
            'Custom World'
            >>> world[template.all()(name="World")]
            ['Custom World']
            >>> # As custom_template isn't qualified by 'a' it cannot be provided. So the default
            ... # implementation is returned instead.
            ... world[template.single(qualified_by='a')("World")]
            'Default World'

        You can customize more finely how the default implementation behaves by applying yourself
        either :py:obj:`.inject` or :py:obj:`.lazy` or deactivate any injection by specifying
        :code:`inject` to be py:obj:`None`.

        Args:
            __func: **/positional-only/** Interface contract for a :py:obj:`.lazy` call.
            inject: */Only a function interface/* Specifying :py:obj:`None` will prevent the use
                of py:obj:`.inject` on the function.
            type_hints_locals: Local variables to use for :py:func:`typing.get_type_hints`. They
                can be explicitly defined by passing a dictionary or automatically detected with
                :py:mod:`inspect` and frame manipulation by specifying :code:`'auto'`. Specifying
                :py:obj:`None` will deactivate the use of locals. The default behavior depends on the
                :py:data:`.config` value of :py:attr:`~.Config.auto_detect_type_hints_locals`. If
                :py:obj:`True` the default value is equivalent to specifying :code:`'auto'`,
                otherwise to :py:obj:`None`.
            catalog: Defines in which catalog the dependency should be registered. Defaults to
                :py:obj:`.world`.

        Returns:
            A :py:class:`.LazyInterface`.

        """
        ...


@API.public
class FunctionInterface(Protocol[P, Out]):
    """
    See :py:class:`.Interface` for an overview and usse :py:obj:`.interface` to create a function
    interface and :py:obj:`.implements` to declare an implementation.
    """

    @property
    def __wrapped__(self) -> Callable[P, Out]:
        """
        Original wrapped function

        .. doctest:: lib_interface_function_wrapped

            >>> from antidote import interface
            >>> @interface
            ... def callback(name: str) -> bool:
            ...     return len(name) < 10
            >>> callback.__wrapped__("short")
            True

        """
        ...

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Dependency[Callable[P, Out]]:
        """
        Constructs a dependency to retrieve a single dependency matching specified constraints.

        .. doctest:: lib_interface_function_single

            >>> from antidote import interface, world, inject, implements
            >>> @interface
            ... def callback(name: str) -> bool:
            ...     ...
            >>> @implements(callback).when(qualified_by='something')
            ... def callback_impl(name: str) -> bool:
            ...     return len(name) < 10
            >>> world[callback.single(qualified_by='something')]
            <function callback_impl ...>

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.

        """
        ...

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Dependency[Sequence[Callable[P, Out]]]:
        """
        Constructs a dependency to retrieve all dependencies matching specified constraints.

        .. doctest:: lib_interface_function_all

            >>> from antidote import interface, world, inject, implements
            >>> @interface
            ... def callback(name: str) -> bool:
            ...     ...
            >>> @implements(callback).when(qualified_by='something')
            ... def callback_impl(name: str) -> bool:
            ...     return len(name) < 10
            >>> world[callback.all(qualified_by='something')]
            [<function callback_impl ...>]

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.

        """
        ...

    def __antidote_dependency_hint__(self) -> Callable[P, Out]:  # for Mypy
        ...


@API.public
class LazyInterface(Protocol[P, Out]):
    """
    See :py:class:`.Interface` for an overview and usse :py:obj:`.interface` to create a function
    interface and :py:obj:`.implements` to declare an implementation.
    """

    # Have to copy-paste LazyFunction for Mypy... error: ParamSpec "P" is unbound
    @property
    def __wrapped__(self) -> Callable[P, Out]:
        """
        Original wrapped function

        .. doctest:: lib_interface_lazy_wrapped

            >>> from antidote import interface
            >>> @interface.lazy
            ... def callback(name: str) -> bool:
            ...     return len(name) < 10
            >>> callback.__wrapped__("short")
            True

        """
        ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Dependency[Out]:
        ...

    def single(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Callable[P, Dependency[Out]]:
        """
        Creates a lazy function with the implementation matching specified constraints.

        .. doctest:: lib_interface_function_single

            >>> from antidote import interface, world, inject, implements
            >>> @interface.lazy
            ... def template(name: str) -> str:
            ...     ...
            >>> @implements.lazy(template).when(qualified_by='something')
            ... def template_impl(name: str) -> str:
            ...     return f"Template {name}"
            >>> world[template.single(qualified_by='something')(name="Bob")]
            'Template Bob'

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.

        """
        ...

    def all(
        self,
        *constraints: PredicateConstraint[Any],
        qualified_by: Optional[object | list[object] | tuple[object, ...]] = None,
        qualified_by_one_of: Optional[list[object] | tuple[object, ...]] = None,
    ) -> Callable[P, Dependency[Sequence[Out]]]:
        """
        Creates a lazy function with the implementations matching specified constraints. The lazy
        function will return a sequence of the implementations calls.

        .. doctest:: lib_interface_lazy_all

            >>> from antidote import interface, world, inject, implements
            >>> @interface.lazy
            ... def template(name: str) -> str:
            ...     ...
            >>> @implements.lazy(template).when(qualified_by='something')
            ... def template_impl(name: str) -> str:
            ...     return f"Template {name}"
            >>> world[template.all(qualified_by='something')(name='Bob')]
            ['Template Bob']

        Args:
            *constraints: :py:class:`.PredicateConstraint` to evaluate for each implementation.
            qualified_by: All specified qualifiers must qualify the implementation.
            qualified_by_one_of: At least one of the specified qualifiers must qualify the
                implementation.

        """
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
        >>> world[Service]
        <ServiceImpl ...>
        >>> world[instanceOf[Service]]  # useful for protocols
        <ServiceImpl ...>
        >>> world[instanceOf(Service)]
        <ServiceImpl ...>
        >>> world[instanceOf(Service).single()]
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

    .. note::

        Adding an (default) implementation and overriding one are thread-safe.

    """

    class protocol(Generic[In]):
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

        def overriding(self, __existing_implementation: In) -> Callable[[C], C]:
            ...

        def as_default(self, __impl: C) -> C:
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
            >>> world[Base]
            <BaseImpl object at ...>
            >>> @implements(Base).overriding(BaseImpl)
            ... class Custom(Base):
            ...     pass
            >>> world[Base]
            <Custom object at ...>

        Trying to override again the same implementation will raise an error:

        .. doctest:: lib_interface_implements_overriding

            >>> @implements(Base).overriding(BaseImpl)
            ... class CustomV2(Base):
            ...     pass
            Traceback (most recent call last):
              File "<stdin>", line 1, in ?
            ValueError: Implementation <class 'BaseImpl'> does not exist.

        Args:
            __existing_implementation: **/positional-only/** Existing implementation to override.

        Returns:
            class decorator

        """
        ...

    def as_default(self, __impl: Any) -> Any:
        """
        .. versionadded: 1.4

        Define a default implementation used when no alternative was found. It can also
        be overridden with :py:meth:`~.implements.overriding`.

        .. doctest:: lib_interface_implements_by_default

            >>> from antidote import interface, implements, world
            >>> @interface
            ... class Base:
            ...     pass
            >>> @implements(Base).as_default
            ... class Default(Base):
            ...     pass
            >>> world[Base]
            <Default object at ...>
            >>> @implements(Base)
            ... class BaseImpl(Base):
            ...     pass
            >>> world[Base]
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
class InterfaceLazyAsDefaultDecorator(Protocol):
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
class ClassImplements(implements, Generic[In], ABC):
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

    def overriding(self, __existing_implementation: In) -> Callable[[C], C]:
        ...

    def as_default(self, __impl: C) -> C:
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
    as_default: LazyImplementsDecorator[P, T]

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

    def as_default(self, __impl: T) -> T:
        ...
