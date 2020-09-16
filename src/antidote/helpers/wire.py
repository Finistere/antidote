import collections.abc as c_abc
import inspect
from typing import Callable, cast, Iterable, Optional, overload, Set, TypeVar, Union

from .._internal.argspec import Arguments
from .._internal.utils import API, SlotsReprMixin
from ..core import DEPENDENCIES_TYPE, raw_inject
from ..core.injection import validate_injection

C = TypeVar('C', bound=type)


class Wiring(SlotsReprMixin):
    @classmethod
    def auto(cls, dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None) -> 'Wiring':
        return Wiring(cls.__auto_methods, dependencies, use_names, use_type_hints,
                      wire_super)

    __slots__ = ('methods', 'dependencies', 'use_names', 'use_type_hints', 'wire_super')
    __auto_methods = set()

    def __init__(self, methods: Iterable[str],
                 dependencies: DEPENDENCIES_TYPE = None,
                 use_names: Union[bool, Iterable[str]] = None,
                 use_type_hints: Union[bool, Iterable[str]] = None,
                 wire_super: Union[bool, Iterable[str]] = None):
        validate_injection(dependencies, use_names, use_type_hints)

        if not isinstance(methods, c_abc.Iterable):
            raise TypeError(f"Methods must be an iterable of method names, "
                            f"not {type(methods)}.")
        elif not isinstance(methods, set):
            methods = set(methods)

        if not (wire_super is None or isinstance(wire_super, (bool, c_abc.Iterable))):
            raise TypeError(
                f"wire_super must be either a boolean or a whitelist of methods names, "
                f"not {type(wire_super)!r}.")

        if wire_super is None:
            wire_super = set()
        elif isinstance(wire_super, bool):
            wire_super = set(methods)

        if not wire_super.issubset(methods):
            raise ValueError(
                f"Method names {wire_super - methods!r} are not specified in methods")

        if isinstance(dependencies, c_abc.Iterable) \
                and not isinstance(dependencies, c_abc.Mapping):
            # convert to Tuple in case we cannot iterate more than once.
            dependencies = tuple(dependencies)

        if isinstance(use_names, c_abc.Iterable):
            use_names = tuple(use_names)

        if isinstance(use_type_hints, c_abc.Iterable):
            use_type_hints = tuple(use_type_hints)

        self.methods: Set[str] = methods
        self.wire_super: Set[str] = wire_super
        self.dependencies = dependencies
        self.use_names = use_names
        self.use_type_hints = use_type_hints

    def is_auto(self):
        return self.methods is Wiring.__auto_methods


@overload
def wire(class_: C,  # noqa: E704  # pragma: no cover
         *,
         wiring: Wiring = None,
         raise_on_missing_method: bool = True
         ) -> C: ...


@overload
def wire(*,  # noqa: E704  # pragma: no cover
         wiring: Wiring = None,
         raise_on_missing_method: bool = True
         ) -> Callable[[C], C]: ...


@API.public
def wire(class_: type = None, *,
         wiring: Wiring = None,
         raise_on_missing_method: bool = True):
    """Wire a class by injecting the dependencies in all specified methods.

    Injection arguments (dependencies, use_names, use_type_hints) are adapted
    for match the arguments of the method. Hence :code:`@inject` won't raise
    an error that it has too much dependencies.

    Args:
        class_: class to wire.
        raise_on_missing_method: Raise an error if a method does exist.
            Defaults to :code:`True`.

    Returns:
        Wired class or a decorator.

    """
    if not isinstance(raise_on_missing_method, bool):
        raise TypeError(f"raise_on_missing must be a boolean, "
                        f"not a {type(raise_on_missing_method)!r}")

    def wire_methods(cls):
        nonlocal wiring
        if not inspect.isclass(cls):
            raise TypeError(f"Expecting a class, got a {type(cls)}")

        cls_wiring = getattr(cls, 'wiring', None)
        if cls_wiring is not None and not isinstance(cls_wiring, Wiring):
            raise TypeError()

        wiring: Wiring = wiring or cast(Wiring, cls_wiring)

        for method_name in wiring.methods:
            method = __get_method(cls, method_name,
                                  with_super=method_name in wiring.wire_super)

            if method is None:
                if raise_on_missing_method:
                    raise TypeError(
                        f"{cls!r} does not have a method named {method_name!r}")
                else:
                    continue  # pragma: no cover

            arguments = Arguments.from_callable(method)
            dependencies = wiring.dependencies
            use_names = wiring.use_names
            use_type_hints = wiring.use_type_hints

            # Restrict injection parameters to those really needed by the method.
            if isinstance(dependencies, c_abc.Mapping):
                dependencies = {
                    arg_name: dependency
                    for arg_name, dependency in dependencies.items()
                    if arg_name in arguments.without_self
                }
            elif isinstance(dependencies, c_abc.Iterable):
                dependencies = dependencies[:len(arguments.without_self)]

            if isinstance(use_names, c_abc.Iterable):
                use_names = [name
                             for name in use_names
                             if name in arguments]

            if isinstance(use_type_hints, c_abc.Iterable):
                use_type_hints = [name
                                  for name in use_type_hints
                                  if name in arguments]

            injected_method = raw_inject(method,
                                         arguments=arguments,
                                         dependencies=dependencies,
                                         use_names=use_names,
                                         use_type_hints=use_type_hints)

            if injected_method is not method:  # If something has changed
                setattr(cls, method_name, injected_method)

        return cls

    return class_ and wire_methods(class_) or wire_methods


def __get_method(cls: type, name: str, with_super: bool) -> Optional[Callable]:
    if with_super:
        for c in cls.__mro__:
            wrapped = c.__dict__.get(name)
            if wrapped is not None:
                return wrapped
    else:
        return cls.__dict__.get(name)

    return None
