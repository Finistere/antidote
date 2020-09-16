from __future__ import annotations

import collections.abc as c_abc
import enum
import inspect
from typing import Callable, final, FrozenSet, Iterable, Optional, overload, TypeVar, \
    Union

from .injection import DEPENDENCIES_TYPE, raw_inject, validate_injection
from .._internal.argspec import Arguments
from .._internal.utils import Copy, FinalImmutable, raw_getattr
from .._internal import API

C = TypeVar('C', bound=type)
_empty_set = frozenset()


@API.public
@final
class Wiring(FinalImmutable):
    """
    Defines how a class should be wired, meaning if/how/which methods are injected. This
    class is intended to be used by configuration objects. If you just want to wire a
    single class, consider using the class decorator :py:func:`~.wire` instead.

    Injection arguments (:code:`dependencies`, :code:`use_names`,  :code:`use_type_hints`)
    are adapted for match the arguments of the method. Hence :py:func:`~.injection.inject`
    won't raise an error that it has too much dependencies.

    Instances are immutable. If you want to change some parameters, typically defaults
    defined by Antidote, you'll need to rely on :py:meth:`~.copy`. It accepts the same
    arguments as :py:meth:`~.__init__` and overrides existing values.

    .. doctest::

        >>> from antidote import Wiring
        >>> # Methods must always be specified.
        ... w = Wiring(methods=['my_method', 'other_method'])
        >>> # Now argument names will be used on both my_method and other_method.
        ... w_copy = w.clone(use_names=True)

    """
    __slots__ = ('methods', 'dependencies', 'use_names', 'use_type_hints', 'wire_super',
                 'ignore_missing_method')
    methods: FrozenSet[str]
    """Method names that must be injected."""
    wire_super: FrozenSet[str]
    """
    Method names which may be retrieved in a parent class. By default, only methods 
    directly defined in the class itself may be injected.
    """
    ignore_missing_method: FrozenSet[str]
    """Method names for which an exception will not be raised if not found."""
    dependencies: DEPENDENCIES_TYPE
    use_names: Union[True, FrozenSet[str]]
    use_type_hints: Union[True, FrozenSet[str]]

    def __init__(self,
                 *,
                 methods: Iterable[str],
                 dependencies: DEPENDENCIES_TYPE = None,
                 use_names: Union[bool, Iterable[str]] = None,
                 use_type_hints: Union[bool, Iterable[str]] = None,
                 wire_super: Union[bool, Iterable[str]] = None,
                 ignore_missing_method: Union[bool, Iterable[str]] = None):
        """
        Args:
            methods: Methods names.
            dependencies: Propagated for every method to :py:func:`~.injection.inject`
            use_names: Propagated for every method to :py:func:`~.injection.inject`
            use_type_hints: Propagated for every method to :py:func:`~.injection.inject`
            wire_super: Method names which may be retrieved in a parent class. By default,
                only methods  directly defined in the class itself may be injected. If
                :py:obj:`True` all methods will be searched in parent classes. Defaults to
                :py:obj:`False`.
            ignore_missing_method:  Method names for which an exception will not be
                raised if not found. If :py:obj:`True`, no exception will be raised if
                any of the methods is missing. Defaults to :py:obj:`False`.
        """
        if not isinstance(methods, c_abc.Iterable) or isinstance(methods, str):
            raise TypeError(f"Methods must be an iterable of method names, "
                            f"not {type(methods)}.")
        else:
            methods = frozenset(methods)
        if len(methods) == 0:
            raise ValueError("At least one method must be wired")
        if not all(isinstance(method, str) for method in methods):
            raise ValueError("Methods are expected to be names (str)")

        if not isinstance(use_names, str) and isinstance(use_names, c_abc.Iterable):
            use_names = frozenset(use_names)
        if not isinstance(use_type_hints, str) and isinstance(use_type_hints,
                                                              c_abc.Iterable):
            use_type_hints = frozenset(use_type_hints)
        validate_injection(dependencies, use_names, use_type_hints)

        if not (wire_super is None or isinstance(wire_super, (bool, c_abc.Iterable))) \
                or isinstance(wire_super, str):
            raise TypeError(
                f"wire_super must be either a boolean or a whitelist of methods names, "
                f"not {type(wire_super)!r}.")
        if wire_super is None or isinstance(wire_super, bool):
            wire_super = bool(wire_super)
        else:
            wire_super = frozenset(wire_super)
            if not wire_super.issubset(methods):
                raise ValueError(f"wire_super is not a subset of methods. "
                                 f"Method names {wire_super - methods!r} are unknown.")

        if isinstance(ignore_missing_method, str) \
                or not (ignore_missing_method is None
                        or isinstance(ignore_missing_method, (bool, c_abc.Iterable))):
            raise TypeError(f"ignore_missing_method must be a boolean or a list of "
                            f"methods names for which an exception must be raised if "
                            f"it's missing, not {type(ignore_missing_method)}")
        if ignore_missing_method is None or isinstance(ignore_missing_method, bool):
            ignore_missing_method = bool(ignore_missing_method)
        else:
            ignore_missing_method = frozenset(ignore_missing_method)
            if not ignore_missing_method.issubset(methods):
                raise ValueError(
                    f"ignore_missing_method is not a subset of methods. "
                    f"Method names {', '.join(map(repr, ignore_missing_method - methods))} "
                    f"are unknown.")

        if isinstance(wire_super, bool):
            wire_super = methods if wire_super else _empty_set
        if isinstance(ignore_missing_method, bool):
            ignore_missing_method = methods if ignore_missing_method else _empty_set

        super().__init__(
            methods=methods,
            wire_super=wire_super,
            dependencies=dependencies,
            use_names=use_names,
            use_type_hints=use_type_hints,
            ignore_missing_method=ignore_missing_method
        )

    def copy(self,
             *,
             methods: Union[Iterable[str], Copy] = Copy.IDENTICAL,
             dependencies: Union[DEPENDENCIES_TYPE, Copy] = Copy.IDENTICAL,
             use_names: Union[bool, Iterable[str], Copy] = Copy.IDENTICAL,
             use_type_hints: Union[bool, Iterable[str], Copy] = Copy.IDENTICAL,
             wire_super: Union[bool, Iterable[str], Copy] = Copy.IDENTICAL,
             ignore_missing_method: Union[bool, Iterable[str], Copy] = Copy.IDENTICAL
             ) -> Wiring:
        """
        Returns:
            Wiring: copy of the current object with the specified attributes overriding
            existing ones.
        """
        return Wiring(
            methods=self.methods if methods is Copy.IDENTICAL else methods,
            dependencies=(self.dependencies
                          if dependencies is Copy.IDENTICAL else
                          dependencies),
            use_names=self.use_names if use_names is Copy.IDENTICAL else use_names,
            use_type_hints=(self.use_type_hints
                            if use_type_hints is Copy.IDENTICAL else
                            use_type_hints),
            wire_super=self.wire_super if wire_super is Copy.IDENTICAL else wire_super,
            ignore_missing_method=(self.ignore_missing_method
                                   if ignore_missing_method is Copy.IDENTICAL else
                                   ignore_missing_method)
        )

    @API.experimental
    def wire(self, klass: C) -> C:
        """**Experimental**

        Used to wire a class with specified configuration.

        Args:
            klass: Class to wired

        Returns:
            The same class object with specified methods injected.
        """
        return _wire_class(klass, self)


@overload
def wire(klass: C,  # noqa: E704  # pragma: no cover
         *,
         methods: Iterable[str],
         dependencies: DEPENDENCIES_TYPE = None,
         use_names: Union[bool, Iterable[str]] = None,
         use_type_hints: Union[bool, Iterable[str]] = None,
         wire_super: Union[bool, Iterable[str]] = None
         ) -> C: ...


@overload
def wire(*,  # noqa: E704  # pragma: no cover
         methods: Iterable[str],
         dependencies: DEPENDENCIES_TYPE = None,
         use_names: Union[bool, Iterable[str]] = None,
         use_type_hints: Union[bool, Iterable[str]] = None,
         wire_super: Union[bool, Iterable[str]] = None
         ) -> Callable[[C], C]: ...


@API.public
def wire(klass: type = None,
         *,
         methods: Iterable[str],
         dependencies: DEPENDENCIES_TYPE = None,
         use_names: Union[bool, Iterable[str]] = None,
         use_type_hints: Union[bool, Iterable[str]] = None,
         wire_super: Union[bool, Iterable[str]] = None):
    """Wire a class by injecting specified methods.

    Injection arguments (:code:`dependencies`, :code:`use_names`,  :code:`use_type_hints`)
    are adapted for match the arguments of the method. Hence :py:func:`~.injection.inject`
    won't raise an error that it has too much dependencies.

    Args:
        klass: Class to wire.
        methods: Method names that must be injected.
        dependencies: Propagated for every method to :py:func:`~.injection.inject`.
        use_names: Propagated for every method to :py:func:`~.injection.inject`.
        use_type_hints: Propagated for every method to :py:func:`~.injection.inject`.
        wire_super: Method names which may be retrieved in a parent class. By default,
            only methods directly defined in the class itself may be injected. If set to
            :py:obj:`True`, it will applied to all methods..

    Returns:
        Wired class or a class decorator.

    """
    wiring = Wiring(
        methods=methods,
        wire_super=wire_super,
        dependencies=dependencies,
        use_names=use_names,
        use_type_hints=use_type_hints
    )

    def wire_methods(cls):
        return _wire_class(cls, wiring)

    return klass and wire_methods(klass) or wire_methods


W = TypeVar('W', bound='WithWiringMixin')


@API.experimental
class WithWiringMixin:
    """**Experimental**

    Used by configuration classes (immutable having a :code:`copy()` method) with a
    :code:`wiring` attribute to change it more simply with the :py:meth:`~.with_wiring`
    method.
    """
    __slots__ = ()

    wiring: Optional[Wiring]

    def copy(self: W, **kwargs) -> W:
        raise NotImplementedError()  # pragma: no cover

    def with_wiring(self: W,
                    *,
                    methods: Union[Iterable[str], Copy] = Copy.IDENTICAL,
                    dependencies: Union[DEPENDENCIES_TYPE, Copy] = Copy.IDENTICAL,
                    use_names: Union[bool, Iterable[str], Copy] = Copy.IDENTICAL,
                    use_type_hints: Union[bool, Iterable[str], Copy] = Copy.IDENTICAL,
                    wire_super: Union[bool, Iterable[str], Copy] = Copy.IDENTICAL,
                    ignore_missing_method: Union[
                        bool, Iterable[str], Copy] = Copy.IDENTICAL
                    ) -> W:
        """
        Accepts the same arguments as :py:class:`~.Wiring`. And behaves the same way
        as :py:meth:`.Wiring.copy`.

        Returns:
            Copy of current instance with its :code:`wiring` attribute modified with
            provided arguments.
        """
        if self.wiring is None:
            if methods is Copy.IDENTICAL:
                raise TypeError("Current wiring is None, so methods must be specified")
            wiring = Wiring(methods=methods)
            return self.copy(
                wiring=wiring.copy(dependencies=dependencies,
                                   use_names=use_names,
                                   use_type_hints=use_type_hints,
                                   wire_super=wire_super,
                                   ignore_missing_method=ignore_missing_method))
        else:
            return self.copy(
                wiring=self.wiring.copy(methods=methods,
                                        dependencies=dependencies,
                                        use_names=use_names,
                                        use_type_hints=use_type_hints,
                                        wire_super=wire_super,
                                        ignore_missing_method=ignore_missing_method))


@API.private  # Used internally for auto wiring.
class AutoWire(enum.Enum):
    auto = object()


@API.private  # Use wire() or Wiring.wire() instead
def _wire_class(cls: C, wiring: Wiring) -> C:
    if not inspect.isclass(cls):
        raise TypeError(f"Expecting a class, got a {type(cls)}")

    for method_name in wiring.methods:
        try:
            method = raw_getattr(cls, method_name,
                                 with_super=method_name in wiring.wire_super)
        except AttributeError:
            if method_name not in wiring.ignore_missing_method:
                raise
        else:
            arguments = Arguments.from_callable(method)
            use_names = wiring.use_names
            use_type_hints = wiring.use_type_hints
            dependencies = wiring.dependencies

            # Restrict injection parameters to those really needed by the method.
            if isinstance(dependencies, c_abc.Mapping):
                dependencies = {
                    arg_name: dependency
                    for arg_name, dependency in dependencies.items()
                    if arg_name in arguments.without_self
                }
            elif isinstance(dependencies, c_abc.Iterable) \
                    and not isinstance(dependencies, str):
                dependencies = dependencies[:len(arguments.without_self)]

            if use_names is not None and not isinstance(use_names, bool):
                use_names = use_names.intersection(arguments.arg_names)

            if use_type_hints is not None and not isinstance(use_type_hints, bool):
                use_type_hints = use_type_hints.intersection(arguments.arg_names)

            # If we're wrapping a static/class-method, we can just re-wrap it so
            # that isinstance(..., classmethod) still works as one would expect.
            injected_method = raw_inject(
                method.__func__
                if isinstance(method, (classmethod, staticmethod)) else
                method,
                arguments=arguments,
                dependencies=dependencies,
                use_names=use_names,
                use_type_hints=use_type_hints
            )

            if isinstance(method, classmethod):
                injected_method = classmethod(injected_method)
            elif isinstance(method, staticmethod):
                injected_method = staticmethod(injected_method)

            if injected_method is not method:  # If something has changed
                setattr(cls, method_name, injected_method)

    return cls
