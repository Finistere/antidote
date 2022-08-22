from __future__ import annotations

import collections.abc as c_abc
import enum
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    FrozenSet,
    Iterable,
    Mapping,
    Optional,
    overload,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from typing_extensions import final, Literal

from .._internal import API, Copy, Default, retrieve_or_validate_injection_locals
from .utils import is_readonly_catalog

if TYPE_CHECKING:
    from . import ReadOnlyCatalog, TypeHintsLocals

__all__ = ["wire", "Wiring", "Methods"]

C = TypeVar("C", bound=type)
_empty_set: FrozenSet[str] = frozenset()


@API.public
@final
class Methods(enum.Enum):
    """
    Enumeration used by :py:class:`.Wiring` and :py:func:`.wire` to define which kind of methods
    to wire. Only one value exists currently, code:`ALL`, which implies injecting all methods.
    """

    ALL = enum.auto()


@API.public
@final
@dataclass(frozen=True, eq=True)
class Wiring:
    """
    Defines how a class should be wired, meaning if/how/which methods are injected. This
    class is intended to be used as a parameter. Consider using :py:func:`.wire` to wire classes
    directly. Instances are immutable.

    .. doctest:: core_Wiring

        >>> from antidote import Wiring, injectable, inject
        >>> @injectable
        ... class Database:
        ...     pass
        >>> @injectable(wiring=Wiring(methods=['my_method']))
        ... class Dummy:
        ...     def my_method(self, db: Database = inject.me()) -> Database:
        ...         return db
        >>> Dummy().my_method()
        <Database ...>

    """

    __slots__ = (
        "methods",
        "fallback",
        "ignore_type_hints",
        "raise_on_double_injection",
    )
    methods: Methods | FrozenSet[str]
    fallback: Mapping[str, object]
    ignore_type_hints: bool
    raise_on_double_injection: bool

    def __init__(
        self,
        *,
        methods: Methods | Iterable[str] = Methods.ALL,
        fallback: Mapping[str, object] | None = None,
        raise_on_double_injection: bool = False,
        ignore_type_hints: bool = False,
    ) -> None:
        """
        Args:
            methods: Names of methods that must be injected. Defaults to all method.
            raise_on_double_injection: Whether an error should be raised if method is already
                injected. Defaults to :py:obj:`False`.
            fallback: Propagated for every method to :py:obj:`.inject`.
            ignore_type_hints: Propagated for every method to :py:obj:`.inject`.

        """
        if not isinstance(raise_on_double_injection, bool):
            raise TypeError(
                f"raise_on_double_injection must be a boolean, "
                f"not {type(raise_on_double_injection)}"
            )

        if isinstance(methods, str) or not isinstance(methods, (c_abc.Iterable, Methods)):
            raise TypeError(f"methods must be an iterable of method names, not {type(methods)}.")
        elif isinstance(methods, c_abc.Iterable):
            methods = frozenset(methods)
            if not all(isinstance(method, str) for method in methods):
                raise TypeError("methods is expected to contain methods names (str)")

        if not isinstance(ignore_type_hints, bool):
            raise TypeError(f"ignore_type_hints must be a boolean, not {type(ignore_type_hints)}")

        if not (
            fallback is None
            or (
                isinstance(fallback, c_abc.Mapping)
                and all(isinstance(key, str) for key in fallback.keys())
            )
        ):
            raise TypeError(
                f"fallback must be a mapping of of argument names to dependencies or None, "
                f"not {type(fallback)!r}"
            )
        elif fallback is not None:
            fallback = dict(fallback)

        object.__setattr__(self, "methods", methods)
        object.__setattr__(self, "fallback", fallback)
        object.__setattr__(self, "raise_on_double_injection", raise_on_double_injection)
        object.__setattr__(self, "ignore_type_hints", ignore_type_hints)

    def copy(
        self,
        *,
        methods: Union[Methods, Iterable[str], Copy] = Copy.IDENTICAL,
        fallback: Union[Mapping[str, object], Copy] = Copy.IDENTICAL,
        raise_on_double_injection: Union[bool, Copy] = Copy.IDENTICAL,
        ignore_type_hints: Union[bool, Copy] = Copy.IDENTICAL,
    ) -> Wiring:
        """
        Copies current wiring and overrides only specified arguments. Accepts the same arguments as
        :py:meth:`~.Wiring.__init__`.
        """
        kwargs: dict[str, Any] = dict(
            methods=self.methods,
            fallback=self.fallback,
            raise_on_double_injection=self.raise_on_double_injection,
            ignore_type_hints=self.ignore_type_hints,
        )
        if methods is not Copy.IDENTICAL:
            kwargs["methods"] = methods
        if fallback is not Copy.IDENTICAL:
            kwargs["fallback"] = fallback
        if raise_on_double_injection is not Copy.IDENTICAL:
            kwargs["raise_on_double_injection"] = raise_on_double_injection
        if ignore_type_hints is not Copy.IDENTICAL:
            kwargs["ignore_type_hints"] = ignore_type_hints
        # Ensure arguments are validated.
        return Wiring(**kwargs)

    def wire(
        self,
        *,
        klass: type,
        app_catalog: ReadOnlyCatalog | None = None,
        type_hints_locals: Optional[Mapping[str, object]] = None,
        class_in_locals: bool | Default = Default.sentinel,
    ) -> None:
        """
        Used to wire a class with specified configuration. It does not return a new class and
        modifies the existing one.

        Args:
            klass: Class to wire.
            type_hints_locals: Propagated for every method to :py:obj:`.inject`.
            app_catalog: Propagated for every method to :py:obj:`.inject`.
            class_in_locals: Whether to add the current class as a local variable. This
                is typically helpful when the class uses itself as a type hint as during the
                wiring, the class has not yet been defined in the globals/locals. The default
                depends on the value of :code:`ignore_type_hints`. If ignored, the class will not
                be added to the :code:`type_hints_locals`. Specifying :code:`type_hints_locals=None`
                does not prevent the class to be added.
        """
        from ._wiring import wire_class

        if not (app_catalog is None or is_readonly_catalog(app_catalog)):
            raise TypeError(
                f"catalog must be a ReadOnlyCatalog or None, " f"not a {type(app_catalog)!r}"
            )

        if not isinstance(klass, type):
            raise TypeError(f"Expecting a class, got a {type(klass)}")

        if type_hints_locals is not None and not isinstance(type_hints_locals, dict):
            raise TypeError(
                f"type_hints_locals must be None or a dict," f"not a {type(type_hints_locals)!r}"
            )
        if class_in_locals is Default.sentinel:
            class_in_locals = not self.ignore_type_hints
        elif not isinstance(class_in_locals, bool):
            raise TypeError(
                f"class_in_locals must be a boolean if specified, "
                f"not a {type(class_in_locals)!r}"
            )

        if class_in_locals:
            if self.ignore_type_hints:
                raise ValueError("class_in_locals cannot be True if ignoring type hints!")
            type_hints_locals = dict(type_hints_locals or {})
            type_hints_locals.setdefault(klass.__name__, klass)

        wire_class(
            klass=klass, wiring=self, type_hints_locals=type_hints_locals, catalog=app_catalog
        )


@overload
def wire(
    __klass: C,
    *,
    methods: Methods | Iterable[str] = ...,
    fallback: Mapping[str, object] | None = ...,
    raise_on_double_injection: bool = ...,
    ignore_type_hints: bool = ...,
    type_hints_locals: TypeHintsLocals = ...,
    app_catalog: ReadOnlyCatalog | None = ...,
) -> C:
    ...


@overload
def wire(
    *,
    methods: Methods | Iterable[str] = ...,
    fallback: Mapping[str, object] | None = ...,
    raise_on_double_injection: bool = ...,
    ignore_type_hints: bool = ...,
    type_hints_locals: TypeHintsLocals = ...,
    app_catalog: ReadOnlyCatalog | None = ...,
) -> Callable[[C], C]:
    ...


@API.public
def wire(
    __klass: C | None = None,
    *,
    methods: Methods | Iterable[str] = Methods.ALL,
    fallback: Mapping[str, object] | None = None,
    raise_on_double_injection: bool = False,
    ignore_type_hints: bool = False,
    type_hints_locals: Union[
        Mapping[str, object], Literal["auto"], Default, None
    ] = Default.sentinel,
    app_catalog: ReadOnlyCatalog | None = None,
) -> Union[C, Callable[[C], C]]:
    """
    Wire a class by injected specified methods. Methods are only replaced if any dependencies were
    detected. The same class is returned, it only modifies the methods.

    .. doctest:: core_wiring_wire

        >>> from antidote import wire, injectable, inject
        >>> @injectable
        ... class MyService:
        ...     pass
        >>> @wire
        ... class Dummy:
        ...     def method(self, service: MyService = inject.me()) -> MyService:
        ...         return service
        >>> Dummy().method()
        <MyService object at ...>

    Args:
        __klass: Class to wire.
        methods: Names of methods that must be injected. Defaults to all method.
        raise_on_double_injection: Whether an error should be raised if method is already
            injected. Defaults to :py:obj:`False`.
        fallback: Propagated for every method to :py:obj:`.inject`.
        ignore_type_hints: Propagated for every method to :py:obj:`.inject`.
        type_hints_locals: Propagated for every method to :py:obj:`.inject`.
        app_catalog: Propagated for every method to :py:obj:`.inject`.

    Returns:
        Wired class or a class decorator.

    """
    wiring = Wiring(
        methods=methods,
        fallback=fallback,
        raise_on_double_injection=raise_on_double_injection,
        ignore_type_hints=ignore_type_hints,
    )

    if wiring.ignore_type_hints:
        w_locals = None
    else:
        w_locals = retrieve_or_validate_injection_locals(type_hints_locals)

    def wire_methods(cls: C) -> C:
        wiring.wire(klass=cls, type_hints_locals=w_locals, app_catalog=app_catalog)
        return cls

    return __klass and wire_methods(__klass) or wire_methods
