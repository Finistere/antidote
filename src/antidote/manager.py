import contextlib
import inspect
import weakref
from typing import (Any, Callable, Dict, Iterable, Mapping, Sequence, Type, TypeVar,
                    Union, cast, get_type_hints)

from antidote.providers import Provider
from antidote.providers.tags import Tag, TagProvider
from ._utils import get_arguments_specification
from .container import DependencyContainer
from .injector import DependencyInjector
from .providers import FactoryProvider, GetterProvider

T = TypeVar('T')


class DependencyManager:
    """Provides utility functions/decorators to manage dependencies.

    Except for :py:meth:`attrib()` all functions can either be used as
    decorators or functions to directly modify an object.

    Custom instances or classes can be used as :py:attr:`container` and
    :py:attr:`injector`.

    """

    def __init__(self,
                 auto_wire: bool = None,
                 use_names: bool = None,
                 arg_map: Mapping = None,
                 container: DependencyContainer = None,
                 injector: DependencyInjector = None
                 ) -> None:
        """Initialize the DependencyManager.

        Args:
            auto_wire: Default value for :code:`auto_wire` argument.
            use_names: Default value for :code:`use_names` argument.
            container: Container to use if specified.
            injector: Injector to use if specified.

        """
        self.auto_wire = auto_wire if auto_wire is not None else True
        self.use_names = use_names if use_names is not None else False
        self.arg_map = dict()  # type: Dict
        self.arg_map.update(arg_map or dict())

        self.container = container or DependencyContainer()  # type: DependencyContainer
        self.container[DependencyContainer] = weakref.proxy(self.container)

        self.injector = injector or DependencyInjector(
            self.container)  # type: DependencyInjector  # noqa
        self.container[DependencyInjector] = weakref.proxy(self.injector)

        self.provider(FactoryProvider)
        self._factories = cast(FactoryProvider, self.providers[FactoryProvider])

        self.provider(GetterProvider)
        self._getters = cast(GetterProvider, self.providers[GetterProvider])

        self.provider(TagProvider)
        self._tags = cast(TagProvider, self.providers[TagProvider])

    def __repr__(self):
        return (
            "{}(auto_wire={!r}, mapping={!r}, use_names={!r}, "
            "container={!r}, injector={!r})"
        ).format(type(self).__name__, self.auto_wire, self.arg_map,
                 self.use_names, self.container, self.injector)

    @property
    def providers(self) -> Dict[Type[Provider], Provider]:
        return self.container.providers

    def inject(self,
               func: Callable = None,
               arg_map: Union[Mapping, Sequence] = None,
               use_names: Union[bool, Iterable[str]] = None,
               use_type_hints: Union[bool, Iterable[str]] = None,
               bind: bool = False
               ) -> Callable:
        """Inject dependencies into the function.

        Args:
            func: Callable for which the argument should be injected.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overridden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.
            bind: bind arguments with :py:func:`functools.partial` directly to
                avoid the overhead of retrieving dependencies. This should only
                be used when necessary, it makes testing a lot more difficult.

        Returns:
            The injected function or a decorator.

        """
        if use_names is None:
            use_names = self.use_names

        def _inject(f):
            _mapping = self.arg_map.copy()
            if isinstance(arg_map, Mapping):
                _mapping.update(arg_map)
            elif isinstance(arg_map, Sequence):
                arg_spec = get_arguments_specification(f)
                for arg, dependency_id in zip(arg_spec.arguments, arg_map):
                    _mapping[arg.name] = dependency_id

            if bind:
                return self.injector.bind(func=f, arg_map=_mapping,
                                          use_names=use_names,
                                          use_type_hints=use_type_hints)

            return self.injector.inject(func=f, arg_map=_mapping,
                                        use_names=use_names,
                                        use_type_hints=use_type_hints)

        return func and _inject(func) or _inject

    def register(self,
                 cls: type = None,
                 singleton: bool = True,
                 auto_wire: Union[bool, Iterable[str]] = None,
                 arg_map: Union[Mapping, Sequence] = None,
                 use_names: Union[bool, Iterable[str]] = None,
                 use_type_hints: Union[bool, Iterable[str]] = None,
                 tags: Iterable[Union[str, Tag]] = None
                 ) -> Union[Callable, type]:
        """Register a dependency by its class.

        Args:
            cls: Class to register as a dependency. It will be instantiated
                only when requested.
            singleton: If True, the class will be instantiated only once,
                further will receive the same instance.
            auto_wire: Injects automatically the dependencies of the methods
                specified, or only of :code:`__init__()` if True.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overridden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.
            tags: Iterable of tags to be applied. Those must be either strings
                (the tags name) or :py:class:`~.providers.tags.Tag`. All
                dependencies with a specific tag can then be retrieved with
                a :py:class:`~.providers.tags.Tagged`.

        Returns:
            The class or the class decorator.

        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        def register_class(_cls):
            _cls = self._prepare_class(_cls,
                                       auto_wire=auto_wire,
                                       arg_map=arg_map,
                                       use_names=use_names,
                                       use_type_hints=use_type_hints)

            self._factories.register(dependency_id=_cls, factory=_cls,
                                     singleton=singleton)

            if tags is not None:
                self._tags.register(_cls, tags)

            return _cls

        return cls and register_class(cls) or register_class

    def factory(self,
                func: Callable = None,
                dependency_id: Any = None,
                auto_wire: Union[bool, Iterable[str]] = None,
                singleton: bool = True,
                arg_map: Union[Mapping, Sequence] = None,
                use_names: Union[bool, Iterable[str]] = None,
                use_type_hints: Union[bool, Iterable[str]] = None,
                build_subclasses: bool = False,
                tags: Iterable[Union[str, Tag]] = None
                ) -> Callable:
        """Register a dependency providers, a factory to build the dependency.

        Args:
            func: Callable which builds the dependency.
            dependency_id: Id of the dependency. Defaults to the return type of
                :code:`func` if specified.
            singleton: If True the dependency_provider is called only once.
                Otherwise it is called anew every time.
            auto_wire: If :code:`func` is a function, its dependencies are
                injected if True. Should :code:`func` be a class with
                :py:func:`__call__`, dependencies of :code:`__init__()` and
                :code:`__call__()` will be injected if True. One may also
                provide an iterable of method names requiring dependency
                injection.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overridden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.
            build_subclasses: If True, subclasses will also be build with this
                factory. If multiple factories are defined, the first in the
                MRO is used.
            tags: Iterable of tags to be applied. Those must be either strings
                (the tags name) or :py:class:`~.providers.tags.Tag`. All
                dependencies with a specific tag can then be retrieved with
                a :py:class:`~.providers.tags.Tagged`.

        Returns:
            object: The dependency_provider

        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        def register_factory(obj):
            nonlocal dependency_id
            factory, return_type_hint = self._prepare_callable(
                obj,
                auto_wire=auto_wire,
                arg_map=arg_map,
                use_names=use_names,
                use_type_hints=use_type_hints
            )

            dependency_id = dependency_id or return_type_hint
            self._factories.register(factory=factory,
                                     singleton=singleton,
                                     dependency_id=dependency_id,
                                     build_subclasses=build_subclasses)

            if tags is not None:
                self._tags.register(dependency_id, tags)

            return obj

        return func and register_factory(func) or register_factory

    def wire(self,
             cls: type = None,
             methods: Iterable[str] = None,
             arg_map: Union[Mapping, Sequence] = None,
             use_names: Union[bool, Iterable[str]] = None,
             use_type_hints: Union[bool, Iterable[str]] = None,
             ) -> Union[Callable, type]:
        """Wire a class by injecting the dependencies in all specified methods.

        Args:
            cls: class to wire.
            methods: Name of the methods for which dependencies should be
                injected. Defaults to all defined methods.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overridden.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.

        Returns:
            type: Wired class.

        """

        def wire_methods(_cls):
            if not inspect.isclass(_cls):
                raise ValueError("Expecting a class, got a {}".format(type(_cls)))

            nonlocal methods

            if methods is None:
                methods = map(
                    lambda m: m[0],  # get only the name
                    inspect.getmembers(
                        _cls,
                        # Retrieve static methods, class methods, methods.
                        predicate=lambda f: (inspect.isfunction(f)
                                             or inspect.ismethod(f))
                    )
                )

            for method in methods:
                setattr(_cls,
                        method,
                        self.inject(getattr(_cls, method),
                                    arg_map=arg_map,
                                    use_names=use_names,
                                    use_type_hints=use_type_hints))

            return _cls

        return cls and wire_methods(cls) or wire_methods

    def attrib(self,
               dependency_id: Any = None,
               use_name: bool = None,
               **attr_kwargs):
        """Injects a dependency with attributes defined with attrs package.

        Args:
            dependency_id: Id of the dependency to inject. Defaults to the
                annotation.
            use_name: If True, use the attribute name as the dependency id
                overriding any annotations.
            **attr_kwargs: Keyword arguments passed on to attr.ib()

        Returns:
            object: attr.Attribute with a attr.Factory.

        """
        try:
            import attr
        except ImportError:
            raise RuntimeError("attrs package must be installed.")

        if use_name is None:
            use_name = self.use_names

        def factory(instance):
            nonlocal dependency_id

            if dependency_id is None:
                cls = instance.__class__
                type_hints = get_type_hints(cls) or {}

                for attribute in attr.fields(cls):
                    # Dirty way to find the attrib annotation.
                    # Maybe attr will eventually provide the annotation ?
                    if isinstance(attribute.default, attr.Factory) \
                            and attribute.default.factory is factory:
                        try:
                            dependency_id = type_hints[attribute.name]
                        except KeyError:
                            if use_name:
                                dependency_id = attribute.name
                                break
                        else:
                            break
                else:
                    raise ValueError(
                        "No dependency could be detected. Please specify "
                        "the parameter `dependency_id` or `use_name=True`."
                        "Annotations may also be used."
                    )

            return self.container[dependency_id]

        return attr.ib(default=attr.Factory(factory, takes_self=True),
                       **attr_kwargs)

    def provider(self,
                 cls: type = None,
                 auto_wire: Union[bool, Iterable[str]] = None,
                 arg_map: Union[Mapping, Sequence] = None,
                 use_names: Union[bool, Iterable[str]] = None,
                 use_type_hints: Union[bool, Iterable[str]] = None,
                 ) -> Union[Callable, type]:
        """Register a providers by its class.

        Args:
            cls: class to register as a provider. The class must have a
                :code:`__antidote_provide()` method accepting as first argument
                the dependency id. Variable keyword and positional arguments
                must be accepted as they may be provided.
            auto_wire: If True, the dependencies of :code:`__init__()` are
                injected. An iterable of method names which require dependency
                injection may also be specified.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overridden.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.

        Returns:
            the providers's class or the class decorator.
        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        def register_provider(_cls):
            if not hasattr(_cls, '__antidote_provide__'):
                raise ValueError("Method __antidote_provide__() "
                                 "must be defined")

            _cls = self._prepare_class(_cls,
                                       auto_wire=auto_wire,
                                       arg_map=arg_map,
                                       use_names=use_names,
                                       use_type_hints=use_type_hints)

            self.container.providers[_cls] = _cls()

            return _cls

        return cls and register_provider(cls) or register_provider

    def getter(self,
               getter: Callable[[str], Any] = None,
               namespace: str = None,
               omit_namespace: bool = None,
               auto_wire: Union[bool, Iterable[str]] = None,
               arg_map: Union[Mapping, Sequence] = None,
               use_names: Union[bool, Iterable[str]] = None,
               use_type_hints: Union[bool, Iterable[str]] = None,
               ) -> Callable:
        """
        Register a mapping of parameters and its associated parser.

        Args:
            getter: Function used to retrieve a requested dependency which will
                be given as an argument. If the dependency cannot be provided,
                it should raise a :py:exc:`LookupError`.
            namespace: Used to identity which getter should be used with a
                dependency, as such they have to be mutually exclusive.
            omit_namespace: Whether or the namespace should be removed from the
                dependency name which is given to the getter. Defaults to False.
            auto_wire: If True, the dependencies of :code:`__init__()` are
                injected. An iterable of method names which require dependency
                injection may also be specified.
            arg_map: Custom mapping of the arguments name to their respective
                dependency id. A sequence of dependencies can also be
                specified, which will be mapped to the arguments through their
                order. Annotations are overridden.
            use_type_hints: Whether the type hints should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments.
            use_names: Whether the arguments name should be used to find for
                a dependency. An iterable of names may also be provided to
                restrict this to a subset of the arguments. Annotations are
                overridden, but not the arg_map.

        Returns:
            getter callable or decorator.
        """

        def register_getter(obj):
            nonlocal namespace, omit_namespace

            if namespace is None:
                namespace = obj.__name__ + ":"
                omit_namespace = omit_namespace if omit_namespace is not None else True

            func, _ = self._prepare_callable(obj,
                                             auto_wire=auto_wire,
                                             arg_map=arg_map,
                                             use_names=use_names,
                                             use_type_hints=use_type_hints)

            self._getters.register(getter=func,
                                   namespace=namespace,
                                   omit_namespace=omit_namespace)

            return func

        return getter and register_getter(getter) or register_getter

    @contextlib.contextmanager
    def context(self,
                dependencies: Union[Mapping, Iterable] = None,
                include: Iterable = None,
                exclude: Iterable = None,
                missing: Iterable = None
                ):
        """
        Creates a context within one can control which of the defined
        dependencies available or not. Any changes will be discarded at the
        end.

        >>> from antidote import antidote, DependencyContainer
        >>> with antidote.context(include=[]):
        ...     # Your code isolated from every other dependencies
        ...     antidote.container[DependencyContainer]
        <... DependencyContainer ...>

        The :py:class:`~antidote.DependencyInjector` and the
        :py:class:`~antidote.DependencyContainer` will still be accessible.

        Args:
            dependencies: Dependencies instances used to override existing ones
                in the new context.
            include: Iterable of dependencies to include. If None
                everything is accessible.
            exclude: Iterable of dependencies to exclude.
            missing: Iterable of dependencies which should raise a
                :py:exc:`~.exceptions.DependencyNotFoundError` even if a
                provider could instantiate them.

        """
        with self.container.context(dependencies=dependencies, include=include,
                                    exclude=exclude, missing=missing):
            # Re-inject DependencyManager's globals
            self.container[DependencyContainer] = weakref.proxy(self.container)
            self.container[DependencyInjector] = weakref.proxy(self.injector)
            yield

    def _prepare_class(self, cls, auto_wire, **inject_kwargs):
        if not inspect.isclass(cls):
            raise ValueError("Expecting a class, got a {}".format(type(cls)))

        if auto_wire:
            cls = self.wire(cls,
                            methods=(('__init__',)
                                     if auto_wire is True else
                                     auto_wire),
                            **inject_kwargs)

        return cls

    def _prepare_callable(self, obj, auto_wire, **inject_kwargs):
        if inspect.isclass(obj):
            # Only way to accurately test if obj has really a __call__()
            # method.
            if '__call__' not in dir(obj):
                raise ValueError("Factory class needs to be callable.")
            type_hints = get_type_hints(obj.__call__)

            if auto_wire:
                obj = self.wire(obj,
                                methods=(('__init__', '__call__')
                                         if auto_wire is True else
                                         auto_wire),
                                **inject_kwargs)

            factory = obj()
        else:
            if not callable(obj):
                raise ValueError("factory parameter needs to be callable.")

            type_hints = get_type_hints(obj)
            factory = self.inject(obj, **inject_kwargs) if auto_wire else obj

        return factory, (type_hints or {}).get('return')
