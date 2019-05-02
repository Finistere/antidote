from typing import Iterable, Union

from .register import register
from .wire import wire
from ..core import DEPENDENCIES_TYPE, DependencyContainer
from ..providers.lazy import LazyMethodCall


class LazyConstantsMeta(type):
    def __new__(metacls, cls, bases, namespace,
                lazy_method: str = 'get',
                auto_wire: Union[bool, Iterable[str]] = None,
                dependencies: DEPENDENCIES_TYPE = None,
                use_names: Union[bool, Iterable[str]] = None,
                use_type_hints: Union[bool, Iterable[str]] = None,
                container: DependencyContainer = None):
        """
        Metaclass used to generate class with constant dependencies.

        This should be used for configuration or external static resources.
        Only public uppercase class attributes will be converted to dependencies.

        .. doctest::

            >>> import antidote
            >>> class Conf(metaclass=antidote.LazyConstantsMeta):
            ...     DOMAIN = 'domain'
            ...     _A = 'unchanged'
            ...     a = 'unchanged'
            ...
            ...     def __init__(self):
            ...         self._data = {'domain': 'example.com'}
            ...
            ...     def get(self, key):
            ...         return self._data[key]
            ...
            >>> Conf._A
            'unchanged'
            >>> Conf.a
            'unchanged'
            >>> Conf().DOMAIN
            'example.com'
            >>> Conf.DOMAIN
            LazyMethodCallDependency(...)
            >>> antidote.world.get(Conf.DOMAIN)
            'example.com'
            >>> @antidote.inject(dependencies=(Conf.DOMAIN,))
            ... def f(a):
            ...     return a
            >>> f()
            'example.com'

        As one can see, neither :code:`a` nor :code:`_A` are changed,
        only :code:`DOMAIN`. Constant's initial value becomes the argument given
        to the lazy method, by default :code:`__call__()`. It has two different
        behaviors depending how it is retrieved:

        - Used as a instance attribute, :code:`Conf().DOMAIN`, is is equivalent
          to :code:`Conf().__call__('domain')`. This lets your code stay easy to
          manipulate and test.
        - Used as a class attribute, :code:`Conf.DOMAIN`, it becomes a special
          object used by Antidote to identify a dependency. This lets you inject
          :code:`Conf.DOMAIN` anywhere in your code.

        The advantage of using this is that Antidote will only instantiate
        :code:`Conf` once, if and only if necessary. The same is applied for
        every constant, those are singletons. Defining your static resources or
        configuration as class constants also makes your code more maintainable,
        as any decent IDE will refactor / find the usage of those in a blink of
        an eye.

        Underneath it uses :py:class:`.LazyMethodCall` and :py:func:`.register`.
        It is equivalent to:

        .. testcode::

            from antidote import LazyMethodCall, register

            @register(auto_wire=('__init__', '__call__'))
            class Conf:
                # Required for the example as we specify __init__() explicitly
                # for auto wiring, so it has to exist.
                def __init__(self):
                    pass

                def __call__(self, key):
                    return config[key]

                DOMAIN = LazyMethodCall(__call__)('domain')

        Args:
            lazy_method: Name of the lazy method to use for the constants.
                Defaults to :code:`'__call__'`.
            auto_wire: Injects automatically the dependencies of the methods
                specified, or only of :code:`__init__()` and :code:`__call__()`
                if True.
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
            container: :py:class:`~.core.container.DependencyContainer` to which the
                dependency should be attached. Defaults to the global container,
                :code:`antidote.world`.
        """
        if lazy_method not in namespace:
            raise ValueError(
                "Lazy method {}() is no defined in {}".format(lazy_method, cls)
            )

        resource_class = super().__new__(metacls, cls, bases, namespace)

        wire_raise_on_missing = True
        if auto_wire is None or isinstance(auto_wire, bool):
            if auto_wire is False:
                methods = ()  # type: Iterable[str]
            else:
                methods = (lazy_method, '__init__')
                wire_raise_on_missing = False
        else:
            methods = auto_wire

        if methods:
            resource_class = wire(
                resource_class,
                methods=methods,
                dependencies=dependencies,
                use_names=use_names,
                use_type_hints=use_type_hints,
                container=container,
                raise_on_missing=wire_raise_on_missing
            )

        resource_class = register(
            resource_class,
            auto_wire=False,
            singleton=True,
            container=container
        )

        func = resource_class.__dict__[lazy_method]
        for name, v in resource_class.__dict__.items():
            if not name.startswith('_') and name.isupper():
                setattr(resource_class, name, LazyMethodCall(func, singleton=True)(v))

        return resource_class

    # Python 3.5 compatibility
    def __init__(metacls, cls, bases, namespace, **kwargs):
        super().__init__(cls, bases, namespace)
