from typing import Callable, Iterable, overload, TypeVar, Union, Type

from .wire import wire
from .._internal.default_container import get_default_container
from ..core import DEPENDENCIES_TYPE, DependencyContainer, DependencyProvider

P = TypeVar('P', bound=Type[DependencyProvider])


@overload
def provider(class_: P,  # noqa: E704  # pragma: no cover
             *,
             auto_wire: Union[bool, Iterable[str]] = True,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             container: DependencyContainer = None
             ) -> P: ...


@overload
def provider(*,  # noqa: E704  # pragma: no cover
             auto_wire: Union[bool, Iterable[str]] = True,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             container: DependencyContainer = None
             ) -> Callable[[P], P]: ...


def provider(class_: Type[DependencyProvider] = None,
             *,
             auto_wire: Union[bool, Iterable[str]] = True,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             container: DependencyContainer = None):
    """Register a providers by its class.

    Args:
        class_: class to register as a provider. The class must have a
            :code:`__antidote_provide()` method accepting as first argument
            the dependency. Variable keyword and positional arguments must be
            accepted as they may be provided.
        auto_wire: If True, the dependencies of :code:`__init__()` are
            injected. An iterable of method names which require dependency
            injection may also be specified.
        dependencies: Can be either a mapping of arguments name to their
            dependency, an iterable of dependencies or a function which returns
            the dependency given the arguments name. If an iterable is specified,
            the position of the arguments is used to determine their respective
            dependency. An argument may be skipped by using :code:`None` as a
            placeholder. Type hints are overridden. Defaults to :code:`None`.
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
        container: :py:class:`~.core.container.DependencyContainer` to which the
            dependency should be attached. Defaults to the global container,
            :code:`antidote.world`.

    Returns:
        the providers's class or the class decorator.
    """
    container = container or get_default_container()

    def register_provider(cls):
        if not issubclass(cls, DependencyProvider):
            raise TypeError("A provider must be subclass of Provider.")

        if auto_wire:
            cls = wire(cls,
                       methods=(('__init__',)
                                if auto_wire is True else
                                auto_wire),
                       dependencies=dependencies,
                       wire_super=wire_super,
                       use_names=use_names,
                       use_type_hints=use_type_hints,
                       container=container,
                       raise_on_missing=auto_wire is not True)

        container.register_provider(cls(container=container))

        return cls

    return class_ and register_provider(class_) or register_provider
