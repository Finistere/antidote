import inspect

from ._compat import PY3
from .injector import DependencyInjector
from .container import DependencyContainer


class DependencyManager(object):
    """Provides utility functions/decorators to manage dependencies.

    Except for :py:meth:`attrib()` all functions can either be used as
    decorators or functions to directly modify an object.

    Custom instances or classes can be used as :py:attr:`container` and
    :py:attr:`injector`.

    """

    auto_wire = True
    """ 
    Default value for :code:`auto_wire` argument in methods such as
    :py:meth:`register()` or :py:meth:`factory()`
    """

    use_arg_name = False
    """ 
    Default value for :code:`use_arg_name` argument in methods such as
    :py:meth:`inject()` or :py:meth:`register()` 
    """

    mapping = None
    """
    Default mapping for :code:`mapping` argument in methods such as
    :py:meth:`inject()` or :py:meth:`register()`.
    """

    def __init__(self, auto_wire=None, use_arg_name=None,
                 container=DependencyContainer,
                 injector=DependencyInjector):
        """Initialize the DependencyManager.

        Args:
            auto_wire (bool, optional): Default value for :code:`auto_wire`
                argument. Defaults to True.
            use_arg_name (bool, optional): Default value for
                :code:`use_arg_name` argument. Defaults to False.
            container (type or object, optional): Either an instance or the
                class of the container to use. Defaults to
                :py:class:`.DependencyContainer`.
            injector (type or object, optional): Either an instance or the
                class of the injector to use. Defaults to
                :py:class:`.DependencyInjector`.
        """
        self.container = (
            container() if isinstance(container, type) else container
        )
        self.injector = (
            injector(self.container)
            if isinstance(injector, type) else
            injector
        )

        if auto_wire is not None:
            self.auto_wire = auto_wire

        if use_arg_name is not None:
            self.use_arg_name = use_arg_name

    def inject(self, func=None, mapping=None, use_arg_name=None, bind=False):
        """Inject the dependency into the function.

        Args:
            func (callable): Callable for which the argument should be
                injected.
            use_arg_name (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            bind (bool, optional): bind arguments with functools.partial
                directly to avoid service retrieval overhead. Defaults to
                False.

        Returns:
            callable: The injected function.

        """
        if use_arg_name is None:
            use_arg_name = self.use_arg_name

        if self.mapping:
            m = self.mapping.copy()
            if mapping:
                m.update(mapping)

            mapping = m

        if bind:
            def _inject(f):
                return self.injector.bind(func=f, mapping=mapping,
                                          use_arg_name=use_arg_name)
        else:
            _inject = self.injector.inject(mapping=mapping,
                                           use_arg_name=use_arg_name)

        return func and _inject(func) or _inject

    def register(self, cls=None, singleton=True, auto_wire=None, mapping=None,
                 use_arg_name=None):
        """Register a dependency by its type or specified id.

        Args:
            cls (object): Object to register as a dependency.
            singleton (bool, optional): A singleton will be only be
                instantiated once. Otherwise the dependency will instantiated
                anew every time. Defaults to True.
            auto_wire (bool or tuple of strings, optional): Injects
                automatically the dependencies of the methods specified, or
                only of :code:`__init__()` if True. Default to True.
            mapping (dict, optional): Custom mapping of the argument s name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_arg_name (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.

        Returns:
            object: The dependency.

        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        def register_service(cls):
            if not inspect.isclass(cls):
                raise ValueError("Expecting a class, found a "
                                 "{}".format(type(cls)))

            if auto_wire:
                cls = self.wire(
                    cls,
                    methods=(
                        ('__init__',) if auto_wire is True else auto_wire
                    ),
                    mapping=mapping,
                    use_arg_name=use_arg_name
                )

            self.container.register(factory=cls, singleton=singleton)

            return cls

        return (
            cls and register_service(cls)
            or register_service
        )

    def factory(self, dependency_factory=None, id=None, hook=None,
                auto_wire=None, singleton=True, mapping=None,
                use_arg_name=None):
        """Register a dependency provider, a factory to build the dependency.

        Args:
            dependency_factory (callable): Callable which builds the
                dependency.
            id (hashable object, optional): Id of the dependency. Defaults to
                the dependency_provider.
            hook (callable, optional): Function which determines if a given id
                matches the factory. Defaults to None.
            singleton (bool, optional): If True the dependency_provider is
                called only once. Otherwise it is called anew every time.
                Defaults to True.
            auto_wire (bool or tuple of strings, optional): Injects
                automatically the dependencies of the methods specified, or
                only of :code:`__init__()` and :code:`__call__()`
                if True. If True and the provider is a function, its arguments
                will be injected. Defaults to True.
            mapping (dict, optional): Custom mapping of the arguments name
                to their respective dependency id. Overrides annotations.
                Defaults to None.
            use_arg_name (bool, optional): Whether the arguments name
                should be used to search for a dependency when no mapping,
                nor annotation is found. Defaults to False.

        Returns:
            object: The dependency_provider

        """
        if auto_wire is None:
            auto_wire = self.auto_wire

        if id is None and hook is None and not PY3:
            raise ValueError("Either a return annotation or the "
                             "'id' parameter must be not None.")

        def register_factory(factory):
            # TODO: `_id` should be replaced with `nonlocal id` once
            # Python 2 support drops.
            _id = None
            if inspect.isclass(factory):
                if auto_wire:
                    factory = self.wire(
                        factory,
                        methods=(
                            ('__call__', '__init__')
                            if auto_wire is True else
                            auto_wire
                        ),
                        mapping=mapping,
                        use_arg_name=use_arg_name
                    )

                factory = factory()

                if not hasattr(factory, '__call__'):
                    raise ValueError('Factory class needs to be callable.')

                if PY3:
                    _id = factory.__call__.__annotations__.get('return')
            else:
                if not callable(factory):
                    raise ValueError('factory parameter needs to be callable.')

                if auto_wire:
                    factory = self.inject(factory,
                                          mapping=mapping,
                                          use_arg_name=use_arg_name)
                if PY3:
                    _id = factory.__annotations__.get('return')

            _id = id or _id

            if not _id and not hook:
                raise ValueError("Either a return annotation or `id` or `hook`"
                                 "parameter must be not None.")

            self.container.register(factory=factory, singleton=singleton,
                                    id=_id, hook=hook)
            return factory

        return (
            dependency_factory and register_factory(dependency_factory)
            or register_factory
        )

    def wire(self, cls=None, methods=None, **inject_kwargs):
        """Wire a class by injecting the dependencies in all specified methods.

        Args:
            cls (type): class to wire.
            methods (tuple of strings, optional): Name of the methods for which
                dependencies should be injected. Defaults to all defined
                methods.
            **inject_kwargs: Keyword arguments passed on to :py:meth:`inject`.

        Returns:
            type: Wired class.

        """
        def wire_methods(cls):
            # TODO: use nonlocal once Python 2.7 support drops.
            _methods = methods
            if not _methods:
                _methods = (
                    name
                    for name, _ in inspect.getmembers(
                        cls,
                        # Retrieve static methods, class methods, methods.
                        predicate=lambda f: (inspect.isfunction(f)
                                             or inspect.ismethod(f))
                    )
                )

            for method in _methods:
                setattr(cls,
                        method,
                        self.inject(getattr(cls, method), **inject_kwargs))

            return cls

        return cls and wire_methods(cls) or wire_methods

    def attrib(self, id=None, use_arg_name=None, **attr_kwargs):
        """Injects a dependency with attributes defined with attrs package.

        Args:
            id (hashable object, optional): Id of the dependency to inject.
                Defaults to the annotation or attribute name if use_arg_name.
            use_arg_name (bool, optional): If True, use the attribute name to
                identify the dependency. Defaults to False.
            **attr_kwargs: Keyword arguments passed on to attr.ib()

        Returns:
            object: attr.Attribute with a attr.Factory.

        """
        try:
            import attr
        except ImportError:
            raise RuntimeError('attrs package must be installed.')

        if use_arg_name is None:
            use_arg_name = self.use_arg_name

        def attrib_factory(instance):
            try:
                _id = attrib_factory.dependency_id
            except AttributeError:
                _id = id
                if _id is None:
                    cls = instance.__class__
                    for attribute in attr.fields(cls):
                        # Dirty way to find the attrib annotation.
                        # Maybe attr will eventually provide the annotation ?
                        if isinstance(attribute.default, attr.Factory) \
                                and attribute.default.factory is attrib_factory:
                            try:
                                _id = cls.__annotations__[attribute.name]
                            except (AttributeError, KeyError):
                                if use_arg_name:
                                    _id = attribute.name
                                    break
                            else:
                                break
                    else:
                        raise ValueError(
                            "No dependency could be detected. Please specify "
                            "the parameter `id` or `use_arg_name=True`. "
                            "Annotations may also be used."
                        )

                attrib_factory.dependency_id = _id

            return self.container[_id]

        return attr.ib(default=attr.Factory(attrib_factory, takes_self=True),
                       **attr_kwargs)
