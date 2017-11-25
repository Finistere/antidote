import threading
import inspect
from collections import deque
from contextlib import contextmanager


from .exception import DependencyError

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap


class DependencyNotFoundError(KeyError, DependencyError):
    """ The dependency could not be found"""


class DependencyInstantiationError(TypeError, DependencyError):
    """ The dependency could not be instantiated """


class DependencyDuplicateError(ValueError, DependencyError):
    """ A dependency already exists with the same id """


class DependencyContainer(object):
    """
    Container of dependencies. Dependencies are either factories which must be
    registered or any user-given data.

    A dependency can be retrieved through its id. The factory of the
    dependency itself is used as its id if none is provided.

    The container uses a cache to instantiate lazily dependencies, deleting and
    setting dependencies only affects the cache, not the registered nor
    user-added dependencies. However, checking whether a dependency is defined
    will search in the cache, the registered and user-added dependencies.
    """

    def __init__(self):
        self._cache = {}
        self._instantiation_lock = threading.RLock()
        self._instantiation_stack = DependencyStack()
        self._factories_registered_by_id = dict()
        self._factories_registered_by_hook = HookDict()
        # Elements in _factories must be either the dependencies themselves or
        # their factory.
        self._factories = ChainMap(
            self._factories_registered_by_id,
            self._factories_registered_by_hook
        )

    def __getitem__(self, id):
        """
        Retrieves the dependency from the cached dependencies. If none matches,
        the container tries to find a matching factory or a matching value in
        the added dependencies.
        """
        try:
            return self._cache[id]
        except KeyError:
            try:
                factory = self._factories[id]
            except KeyError:
                raise DependencyNotFoundError(id)

        try:
            with self._instantiation_stack.instantiating(id):
                if not getattr(factory, 'singleton', True):
                    return factory()

                with self._instantiation_lock:
                    if id not in self._cache:
                        if getattr(factory, 'takes_id', False):
                            self._cache[id] = factory(id)
                        else:
                            self._cache[id] = factory()

        except DependencyError:
            raise

        except Exception as e:
            raise DependencyInstantiationError(repr(e))

        return self._cache[id]

    def __setitem__(self, id, dependency):
        """
        Set a dependency in the cache.
        """
        self._cache[id] = dependency

    def __delitem__(self, id):
        """
        Remove dependency from the cache. Beware that this will not remove
        registered dependencies or user-added dependencies.
        """
        try:
            del self._cache[id]
        except KeyError:
            if id not in self._factories:
                raise DependencyNotFoundError(id)

    def __contains__(self, id):
        """
        Check whether the dependency is in the cache, the registered
        dependencies, or user-added dependencies.
        """
        return id in self._cache or id in self._factories

    def update(self, dependencies):
        """
        Update the cached dependencies.
        """
        self._cache.update(dependencies)

    def register(self, factory, id=None, hook=None, singleton=True):
        """Register a dependency factory by the type of the dependency.

        The dependency can either be registered with an id (the type of the
        dependency if not specified) or a hook.

        Args:
            factory (callable): Callable to be used to instantiate the
                dependency.
            id (object, optional): Id of the dependency, by which it is
                identified. Defaults to the type of the factory.
            hook (callable, optional): Function which determines if a given id
                matches the factory. Defaults to None.
            singleton (bool, optional): A singleton will be only be
                instantiated once. Otherwise the dependency will instantiated
                anew every time.
        """
        if not callable(factory):
            raise ValueError("The `factory` must be callable.")

        dependency_factory = DependencyFactory(factory=factory,
                                               singleton=singleton,
                                               takes_id=hook is not None)

        if hook:
            if not callable(hook):
                raise ValueError("`hook` must be callable.")

            self._factories_registered_by_hook[hook] = dependency_factory
        else:
            id = id or factory

            if id in self._factories_registered_by_id:
                raise DependencyDuplicateError(id)

            self._factories_registered_by_id[id] = dependency_factory

    def extend(self, dependency_factories):
        """Extend the container with a dictionary of default dependencies.

        The additional dependencies definitions are only used if it could not
        be found in the current container.

        Args:
            dependency_factories (dict): Dictionary of factories providing
                the dependency associated with their key.

        """
        self._factories.maps.append(dependency_factories)

    def override(self, dependency_factories):
        """Override any existing definition of dependencies.

        Args:
            dependency_factories (dict): Dictionary of factories providing
                the dependency associated with their key.

        """
        self._factories.maps = [dependency_factories] + self._factories.maps


class HookDict(object):
    def __init__(self):
        self._hook_value = []

    def __setitem__(self, hook, value):
        self._hook_value.append((hook, value))

    def __getitem__(self, item):
        for hook, value in self._hook_value:
            if hook(item):
                return value

        raise KeyError(item)

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        else:
            return True


class DependencyFactory(object):
    __slots__ = ('factory', 'singleton', 'takes_id')

    def __init__(self, factory, singleton, takes_id):
        self.factory = factory
        self.singleton = singleton
        self.takes_id = takes_id

    def __call__(self, *args, **kwargs):
        return self.factory(*args, **kwargs)


class DependencyStack(object):
    def __init__(self, stack=None):
        self._stack = deque(stack or [])
        self._dependencies = set(self._stack)

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            self.format_stack()
        )

    __str__ = __repr__

    def __iter__(self):
        return iter(self._stack)

    def format_stack(self, sep=' => '):
        return sep.join(map(self._format_dependency_id, self._stack))

    @classmethod
    def _format_dependency_id(cls, id):
        if inspect.isclass(id):
            return "{}.{}".format(id.__module__, id.__name__)

        return repr(id)

    @contextmanager
    def instantiating(self, id):
        if id in self._dependencies:
            stack = self._stack
            stack.append(id)
            self._clear()
            raise DependencyCycleError(type(self)(stack))

        self._stack.append(id)
        self._dependencies.add(id)
        yield
        self._dependencies.remove(self._stack.pop())

    def _clear(self):
        self._stack = deque()
        self._dependencies = set()


class DependencyCycleError(RuntimeError, DependencyError):
    """ Error raised when a dependency cycle is found """

    def __init__(self, dependency_stack):
        self.dependency_stack = dependency_stack
        super(DependencyCycleError, self).__init__()

    def __str__(self):
        return " A dependency cycle is found: {}".format(
            self.dependency_stack.format_stack()
        )
