from typing import Any, Callable, cast, Iterable, Union

from .._internal.default_container import get_default_container
from .._internal.helpers import prepare_callable
from ..core import DEPENDENCIES_TYPE, DependencyContainer
from ..providers import ResourceProvider


def resource(func: Callable[[str], Any] = None,
             *,
             namespace: str = None,
             priority: float = 0,
             auto_wire: Union[bool, Iterable[str]] = True,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             wire_super: Union[bool, Iterable[str]] = None,
             container: DependencyContainer = None
             ) -> Callable:
    """
    Register a mapping of parameters and its associated parser.

    Args:
        func: Function used to retrieve a requested dependency which will
            be given as an argument. If the dependency cannot be provided,
            it should raise a :py:exc:`LookupError`.
        namespace: Used to identity which getter should be used with a
            dependency. It should only contain characters in
            :code:`[a-zA-Z0-9_]`.
        priority: Used to determine which getter should be called first when
            they share the same namespace. Highest priority wins. Defaults to
            0.
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
        container: :py:class:~.core.base.DependencyContainer` to which the
            dependency should be attached. Defaults to the global core if
            it is defined.

    Returns:
        getter callable or decorator.
    """
    container = container or get_default_container()

    def register_resource(obj):
        nonlocal namespace

        if namespace is None:
            namespace = obj.__name__

        obj, getter, _ = prepare_callable(obj,
                                          auto_wire=auto_wire,
                                          wire_super=wire_super,
                                          dependencies=dependencies,
                                          use_names=use_names,
                                          use_type_hints=use_type_hints,
                                          container=container)

        resource_provider = cast(ResourceProvider,
                                 container.providers[ResourceProvider])
        resource_provider.register(getter=getter,
                                   namespace=namespace,
                                   priority=priority)

        return obj

    return func and register_resource(func) or register_resource
