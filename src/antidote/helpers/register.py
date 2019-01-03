import inspect
import collections.abc as c_abc
from typing import Callable, cast, Iterable, Union

from .wire import wire
from .._internal.default_container import get_default_container
from ..core import DEPENDENCIES_TYPE, DependencyContainer, inject
from antidote.core import Lazy
from ..providers.service import ServiceProvider
from ..providers.tag import Tag, TagProvider


def register(class_: type = None,
             *,
             singleton: bool = True,
             factory: Union[Callable, str] = None,
             auto_wire: Union[bool, Iterable[str]] = None,
             use_mro: Union[bool, Iterable[str]] = None,
             dependencies: DEPENDENCIES_TYPE = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             tags: Iterable[Union[str, Tag]] = None,
             container: DependencyContainer = None
             ) -> Union[Callable, type]:
    """Register a dependency by its class.

    Args:
        class_: Class to register as a dependency. It will be instantiated
            only when requested.
        singleton: If True, the class will be instantiated only once,
            further will receive the same instance.
        factory: Callable to be used when building the class, this allows to
            re-use the same factory for subclasses for example. The dependency
            is given as first argument. If a string is specified, it is
            interpreted as the name of the method which has to be used to build
            the class. The dependency is given as first argument for static
            methods but not for class methods.
        auto_wire: Injects automatically the dependencies of the methods
            specified, or only of :code:`__init__()` if True.
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
        tags: Iterable of tag to be applied. Those must be either strings
            (the tag name) or :py:class:`~.providers.tag.Tag`. All
            dependencies with a specific tag can then be retrieved with
            a :py:class:`~.providers.tag.Tagged`.
        container: :py:class:~.core.base.DependencyContainer` to which the
            dependency should be attached. Defaults to the global core if
            it is defined.

    Returns:
        The class or the class decorator.

    """
    container = container or get_default_container()
    auto_wire = auto_wire if auto_wire is not None else True
    ignore_missing_methods = False

    if auto_wire is True:
        if isinstance(factory, str):
            methods = (factory,)
            if use_mro is None:
                use_mro = (factory,)
        else:
            ignore_missing_methods = True
            methods = ('__init__',)
    elif auto_wire is False:
        pass
    elif isinstance(auto_wire, c_abc.Iterable):
        methods = tuple(auto_wire)
    else:
        raise TypeError("auto_wire must be a boolean or an iterable of "
                        "method names.")

    def register_service(cls):
        nonlocal factory

        if not inspect.isclass(cls):
            raise TypeError("Expected a class, got {!r}".format(cls))

        takes_dependency = True

        # If the factory is the class itself or if it's a classmethod, it is
        # not necessary to inject the dependency.
        if factory is None or (isinstance(factory, str)
                               and inspect.ismethod(getattr(cls, factory))):
            takes_dependency = False

        if auto_wire:
            cls = wire(cls,
                       methods=methods,
                       use_mro=use_mro,
                       dependencies=dependencies,
                       use_names=use_names,
                       use_type_hints=use_type_hints,
                       container=container,
                       ignore_missing_methods=ignore_missing_methods)

        if factory is None or isinstance(factory, Lazy):
            pass
        elif isinstance(factory, str):
            factory = getattr(cls, factory)
        elif inspect.isfunction(factory):
            if auto_wire:
                factory = inject(factory,
                                 dependencies=dependencies,
                                 use_names=use_names,
                                 use_type_hints=use_type_hints,
                                 container=container)
        else:
            raise TypeError("factory must be either a method name, a function, or a "
                            "lazy dependency, not {!r}".format(type(factory)))

        service_provider = cast(ServiceProvider, container.providers[ServiceProvider])
        service_provider.register(service=cls,
                                  factory=factory,
                                  singleton=singleton,
                                  takes_dependency=takes_dependency)

        if tags is not None:
            tag_provider = cast(TagProvider, container.providers[TagProvider])
            tag_provider.register(cls, tags)

        return cls

    return class_ and register_service(class_) or register_service
