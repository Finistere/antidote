from typing import Iterable, Union

from .wire import wire
from .._internal.default_container import get_default_container
from ..core import DEPENDENCIES_TYPE, DependencyContainer, DependencyProvider


def provider(class_: type = None,
             *,
             auto_wire: Union[bool, Iterable[str]] = True,
             use_mro: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
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
        container: :py:class:~.core.base.DependencyContainer` to which the
            dependency should be attached. Defaults to the global core if
            it is defined.

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
                       use_mro=use_mro,
                       use_names=use_names,
                       use_type_hints=use_type_hints,
                       container=container,
                       ignore_missing_methods=auto_wire is True)

        container.register_provider(cls(container=container))

        return cls

    return class_ and register_provider(class_) or register_provider
