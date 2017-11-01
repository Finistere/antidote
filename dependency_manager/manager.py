import inspect

import wrapt

from ._compat import PY3
from .injector import DependencyInjector
from .container import DependencyContainer


class DependencyManager:
    """Provides utility functions/decorators to manage dependencies.

    Except for attirb(). All functions can either be used as decorators or
    functions to directly modify an object.

    If one wishes to use a custom container and/or injector for further
    customization, those only need to implement the following methods:
    - container: __getitem__(), __setitem__(), register()
    - injector: generate_arguments_mapping(), generate_injected_args_kwargs()
    """
    auto_wire = True
    use_arg_name = False

    def __init__(self, auto_wire=None, use_arg_name=None,
                 container=DependencyContainer,
                 injector=DependencyInjector):
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

    def register(self, dependency=None, id=None, singleton=True,
                 auto_wire=None, mapping=None, use_arg_name=None):
        """Register a dependency by its type or specified id.

        Args:
            dependency (object): Object to register as a dependency.
            id (hashable object, optional): Id of the dependency. Defaults to
                the type of the dependency.
            singleton (bool, optional): A singleton will be only be
                instantiated once. Otherwise the dependency will instantiated
                anew every time. Defaults to True.
            auto_wire (bool or tuple of strings, optional): Injects
                automatically the dependencies of the methods specified, or
                only of __init__() if True. Default to False.
            mapping (dict, optional): Custom mapping of the arguments name
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

        def register_dependency(dependency):
            if inspect.isclass(dependency):
                if auto_wire:
                    dependency = self.wire(
                        dependency,
                        methods=(
                            ('__init__',) if auto_wire is True else auto_wire
                        ),
                        mapping=mapping,
                        use_arg_name=use_arg_name
                    )
                self.container.register(factory=dependency,
                                        singleton=singleton)
            else:
                self.container[id or type(dependency)] = dependency

            return dependency

        return (
            dependency and register_dependency(dependency)
            or register_dependency
        )

    def provider(self, dependency_provider=None, id=None, auto_wire=None,
                 singleton=True, mapping=None, use_arg_name=None):
        """Register a dependency provider, a factory to build the dependency.

        Args:
            dependency_provider (callable): Callable which builds the
                dependency.
            id (hashable object, optional): Id of the dependency. Defaults to
                the dependency_provider.
            singleton (bool, optional): If True the dependency_provider is
                called only once. Otherwise it is called anew every time.
                Defaults to True.
            auto_wire (bool or tuple of strings, optional): Injects
                automatically the dependencies of the methods specified, or
                only of __init__() and __call__() if True. If True and the
                provider is a function, its arguments will be injected.
                Defaults to False.
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

        if id is None and not PY3:
            raise ValueError("Either a return annotation or the "
                             "'id' parameter must be not None.")

        def register_provider(provider):
            # TODO: `_id` should be replaced with `nonlocal id` once
            # Python 2 support drops.
            _id = None
            if inspect.isclass(provider):
                if auto_wire:
                    provider = self.wire(
                        provider,
                        methods=(
                            ('__call__', '__init__')
                            if auto_wire is True else
                            auto_wire
                        ),
                        mapping=mapping,
                        use_arg_name=use_arg_name
                    )
                if PY3:
                    _id = provider.__call__.__annotations__.get('return')
                provider = provider()
            else:
                if auto_wire:
                    provider = self.inject(provider,
                                           mapping=mapping,
                                           use_arg_name=use_arg_name)
                if PY3:
                    _id = provider.__annotations__.get('return')

            _id = id or _id

            if not _id:
                raise ValueError("Either a return annotation or the "
                                 "'id' parameter must be not None.")

            self.container.register(factory=provider, singleton=singleton,
                                    id=_id)
            return provider

        return (
            dependency_provider and register_provider(dependency_provider)
            or register_provider
        )

    def wire(self, cls=None, methods=None, **inject_kwargs):
        """Wire a class by injecting the dependencies in all specified methods.

        Args:
            cls (type): class to wire.
            methods (tuple of strings, optional): Name of the methods for which
                dependencies should be injected. Defaults to all defined
                methods.
            **inject_kwargs: Keyword arguments passed on to inject.

        Returns:
            type: Wired class.

        """
        def wire_methods(cls):
            # TODO: use nonlocal once Python 2.7 support drops.
            _methods = methods
            if not _methods:
                _methods = inspect.getmembers(
                    cls,
                    # Retrieve static methods, class methods, methods.
                    predicate=lambda f: (inspect.isfunction(f)
                                         or inspect.ismethod(f))
                )

            for method in _methods:
                setattr(cls,
                        method,
                        self.inject(getattr(cls, method), **inject_kwargs))

            return cls

        return cls and wire_methods(cls) or wire_methods

    def inject(self, func=None, mapping=None, use_arg_name=None):
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

        Returns:
            callable: The injected function.

        """
        if use_arg_name is None:
            use_arg_name = self.use_arg_name

        gen_args_kwargs = self.injector.generate_injected_args_kwargs

        @wrapt.decorator
        def fast_inject(wrapped, instance, args, kwargs):
            try:
                arg_mapping = fast_inject.arg_mapping
            except AttributeError:
                arg_mapping = self.injector.generate_arguments_mapping(
                    wrapped,
                    use_arg_name=use_arg_name,
                    mapping=mapping,
                )
                fast_inject.arg_mapping = arg_mapping

            args, kwargs = gen_args_kwargs(arg_mapping, args, kwargs)
            return wrapped(*args, **kwargs)

        return func and fast_inject(func) or fast_inject

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
                    for name, value in cls.__dict__.items():
                        # Dirty way to find the attrib annotation.
                        # Maybe attr will eventually provide the annotation ?
                        if isinstance(value, attr.Attribute) \
                                and isinstance(value.default, attr.Factory) \
                                and value.default.factory is attrib_factory:
                            try:
                                _id = cls.__annotations__[name]
                            except (AttributeError, KeyError):
                                if use_arg_name:
                                    _id = name
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
