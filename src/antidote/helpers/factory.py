from typing import Callable, cast, Iterable, Union

from .._internal.default_container import get_default_container
from .._internal.helpers import prepare_callable
from ..core import DEPENDENCIES_TYPE, DependencyContainer
from ..providers.service import ServiceProvider
from ..providers.tag import Tag, TagProvider


def factory(func: Callable = None,
            *,
            auto_wire: Union[bool, Iterable[str]] = True,
            singleton: bool = True,
            dependencies: DEPENDENCIES_TYPE = None,
            use_names: Union[bool, Iterable[str]] = None,
            use_type_hints: Union[bool, Iterable[str]] = None,
            wire_super: Union[bool, Iterable[str]] = None,
            tags: Iterable[Union[str, Tag]] = None,
            container: DependencyContainer = None
            ) -> Callable:
    """Register a dependency providers, a factory to build the dependency.

    Args:
        func: Callable which builds the dependency.
        singleton: If True, `func` will only be called once. If not it is
            called at each injection.
        auto_wire: If :code:`func` is a function, its dependencies are
            injected if True. Should :code:`func` be a class with
            :py:func:`__call__`, dependencies of :code:`__init__()` and
            :code:`__call__()` will be injected if True. One may also
            provide an iterable of method names requiring dependency
            injection.
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
        tags: Iterable of tag to be applied. Those must be either strings
            (the tag name) or :py:class:`~.providers.tag.Tag`. All
            dependencies with a specific tag can then be retrieved with
            a :py:class:`~.providers.tag.Tagged`.
        container: :py:class:~.core.base.DependencyContainer` to which the
            dependency should be attached. Defaults to the global core if
            it is defined.

    Returns:
        object: The dependency_provider

    """
    container = container or get_default_container()

    def register_factory(obj):
        obj, factory_, return_type_hint = prepare_callable(
            obj,
            auto_wire=auto_wire,
            wire_super=wire_super,
            container=container,
            dependencies=dependencies,
            use_names=use_names,
            use_type_hints=use_type_hints
        )

        if return_type_hint is None:
            raise ValueError("No dependency defined.")

        service_provider = cast(ServiceProvider,
                                container.providers[ServiceProvider])
        service_provider.register(factory=factory_,
                                  singleton=singleton,
                                  service=return_type_hint,
                                  takes_dependency=False)

        if tags is not None:
            tag_provider = cast(TagProvider, container.providers[TagProvider])
            tag_provider.register(dependency=return_type_hint,
                                  tags=tags)

        return obj

    return func and register_factory(func) or register_factory
