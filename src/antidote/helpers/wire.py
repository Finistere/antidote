import collections.abc as c_abc
import inspect
from typing import Callable, Iterable, Optional, overload, Set, TypeVar, Union

from .._internal.argspec import Arguments
from ..core import DEPENDENCIES_TYPE, DependencyContainer, inject

C = TypeVar('C', bound=type)


@overload
def wire(class_: C,  # noqa: E704  # pragma: no cover
         *,
         methods: Iterable[str],
         dependencies: DEPENDENCIES_TYPE = None,
         use_names: Union[bool, Iterable[str]] = None,
         use_type_hints: Union[bool, Iterable[str]] = None,
         wire_super: Union[bool, Iterable[str]] = None,
         container: DependencyContainer = None,
         raise_on_missing: bool = True
         ) -> C: ...


@overload
def wire(*,  # noqa: E704  # pragma: no cover
         methods: Iterable[str],
         dependencies: DEPENDENCIES_TYPE = None,
         use_names: Union[bool, Iterable[str]] = None,
         use_type_hints: Union[bool, Iterable[str]] = None,
         wire_super: Union[bool, Iterable[str]] = None,
         container: DependencyContainer = None,
         raise_on_missing: bool = True
         ) -> Callable[[C], C]: ...


def wire(class_: type = None,
         *,
         methods: Iterable[str],
         dependencies: DEPENDENCIES_TYPE = None,
         use_names: Union[bool, Iterable[str]] = None,
         use_type_hints: Union[bool, Iterable[str]] = None,
         wire_super: Union[bool, Iterable[str]] = None,
         container: DependencyContainer = None,
         raise_on_missing: bool = True
         ) -> Union[Callable, type]:
    """Wire a class by injecting the dependencies in all specified methods.

    Injection arguments (dependencies, use_names, use_type_hints) are adapted
    for match the arguments of the method. Hence :code:`@inject` won't raise
    an error that it has too much dependencies.

    Args:
        class_: class to wire.
        methods: Name of the methods for which dependencies should be
            injected. Defaults to all defined methods.
        dependencies: Can be either a mapping of arguments name to their
            dependency, an iterable of dependencies or a function which returns
            the dependency given the arguments name. If an iterable is specified,
            the position of the arguments is used to determine their respective
            dependency. An argument may be skipped by using :code:`None` as a
            placeholder. The first argument is always ignored for methods (self)
            and class methods (cls).Type hints are overridden. Defaults to :code:`None`.
        use_names: Whether or not the arguments' name should be used as their
            respective dependency. An iterable of argument names may also be
            supplied to restrict this to those. Defaults to :code:`False`.
        use_type_hints: Whether or not the type hints (annotations) should be
            used as the arguments dependency. An iterable of argument names may
            also be specified to restrict this to those. Any type hints from
            the builtins (str, int...) or the typing (:py:class:`~typing.Optional`,
            ...) are ignored. Defaults to :code:`True`.
        wire_super: If a method from a super-class needs to be wired, specify
            either a list of method names or :code:`True` to enable it for
            all methods. Defaults to :code:`False`, only methods defined in the
            class itself can be wired.
        container: :py:class:`~.core.container.DependencyContainer` from which
            the dependencies should be retrieved. Defaults to the global
            core if it is defined.
        raise_on_missing: Raise an error if a method does exist.
            Defaults to :code:`True`.

    Returns:
        Wired class or a decorator.

    """
    if not isinstance(methods, c_abc.Iterable):
        raise TypeError("methods must be either None or an iterable.")

    methods = set(methods)
    wire_super = _validate_wire_super(wire_super, methods)

    if not isinstance(raise_on_missing, bool):
        raise TypeError("raise_on_missing must be a boolean, "
                        "not a {!r}".format(type(raise_on_missing)))

    if isinstance(dependencies, c_abc.Iterable) \
            and not isinstance(dependencies, c_abc.Mapping):
        # convert to Tuple in case we cannot iterate more than once.
        dependencies = tuple(dependencies)

    def wire_methods(cls):
        if not inspect.isclass(cls):
            raise TypeError("Expecting a class, got a {}".format(type(cls)))

        for method_name in methods:
            method = _get_method(cls, method_name,
                                 with_super=method_name in wire_super)

            if method is None:
                if raise_on_missing:
                    raise TypeError("{!r} does not have a method "
                                    "named {!r}".format(cls, method_name))
                else:
                    continue  # pragma: no cover

            arguments = Arguments.from_callable(method)
            _dependencies = dependencies
            _use_names = use_names
            _use_type_hints = use_type_hints

            # Restrict injection parameters to those really needed by the method.
            if isinstance(dependencies, c_abc.Mapping):
                _dependencies = {
                    arg_name: dependency
                    for arg_name, dependency in dependencies.items()
                    if arg_name in arguments.without_self
                }
            elif isinstance(dependencies, c_abc.Iterable):
                _dependencies = dependencies[:len(arguments.without_self)]

            if isinstance(use_names, c_abc.Iterable):
                _use_names = [name
                              for name in use_names
                              if name in arguments]

            if isinstance(use_type_hints, c_abc.Iterable):
                _use_type_hints = [name
                                   for name in use_type_hints
                                   if name in arguments]

            injected_method = inject(method,
                                     arguments=arguments,
                                     dependencies=_dependencies,
                                     use_names=_use_names,
                                     use_type_hints=_use_type_hints,
                                     container=container)

            if injected_method is not method:  # If something has changed
                setattr(cls, method_name, injected_method)

        return cls

    return class_ and wire_methods(class_) or wire_methods


def _validate_wire_super(wire_super: Optional[Union[bool, Iterable[str]]],
                         methods: Set[str]) -> Set[str]:
    if wire_super is None:
        return set()

    if isinstance(wire_super, bool):
        return set(methods) if wire_super else set()

    if isinstance(wire_super, c_abc.Iterable):
        wire_super = set(wire_super)
        if not wire_super.issubset(methods):
            raise ValueError(
                "Method names {!r} are not specified "
                "not specified in methods".format(wire_super - methods)
            )
        return wire_super

    raise TypeError("wire_super must be either a boolean "
                    "or an iterable of method names.")


def _get_method(cls: type, name: str, with_super: bool) -> Optional[Callable]:
    if with_super:
        for c in cls.__mro__:
            wrapped = c.__dict__.get(name)
            if wrapped is not None:
                return wrapped
    else:
        return cls.__dict__.get(name)

    return None
