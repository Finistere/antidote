Advanced Usage
==============


.. testsetup:: advanced_usage

    from antidote import antidote
    antidote.container['name'] = 'Antidote'


Advanced auto-wiring
--------------------

Dependencies having often dependencies themselves, thus Antidote injects them
automatically. That is named "auto-wiring", as dependencies are wired together.
By default, :py:meth:`~.DependencyManager.register` will apply
:py:meth:`~.DependencyManager.inject` to the :code:`__init__` method of your
service. In order to customize how injection.

.. testcode:: advanced_usage

    @antidote.register(use_names=True)
    class Service:
        def __init__(self, name):
            self.name = name

.. doctest:: advanced_usage

    >>> service = antidote.container[Service]
    >>> service.name
    'Antidote'

:py:meth:`~.DependencyManager.register` accepts :code:`use_names` and
:code:`arg_map` parameters with the same meaning as those from
:py:meth:`~.DependencyManager.inject`. By default only :code:`__init__()` is
injected. :py:meth:`~.DependencyManager.factory` also wires :code:`__call__()`
if applied on a class (to create
:ref:`stateful factories <advanced_usage:Stateful factory>` for example).

If you need to wire multiples methods, you only need to specify them:

.. testcode:: advanced_usage

    @antidote.register(use_names=True, auto_wire=('__init__', 'get'))
    class Service:
        def __init__(self, name):
            self.name = name

        def get(self, name):
            return name

.. doctest:: advanced_usage

    >>> service = antidote.container[Service]
    >>> service.get()
    'Antidote'

Auto-wiring can also be deactivated if necessary:

.. testcode:: advanced_usage

    @antidote.register(auto_wire=False)
    class BrokenService:
        def __init__(self, name):
            self.name = name

.. doctest:: advanced_usage

    >>> service = antidote.container[BrokenService]
    Traceback (most recent call last):
        ...
    antidote.exceptions.DependencyInstantiationError: <class 'BrokenService'>


Advanced Factories
------------------

Subclasses Instantiation
^^^^^^^^^^^^^^^^^^^^^^^^

A factory handling subclasses is a common pattern, thus it is made easy to do
so by using the parameter :code:`build_subclasses`:

.. testcode:: advanced_usage

    class Service:
        def __init__(self, name):
            self.name = name

    class SubService(Service):
        pass

    @antidote.factory(build_subclasses=True, use_names=True)
    def service_factory(cls, name) -> Service:
        return cls(name)

.. doctest:: advanced_usage

    >>> s = antidote.container[SubService]
    >>> type(s)
    <class 'SubService'>
    >>> s.name
    'Antidote'

The class requested will be passed as first argument if :code:`build_subclasses`
is set to :py:obj:`True`.

.. note::

    If a class :code:`C` has multiple base classes with a registered factory,
    Antidote searches :code:`C.__mro__` for the first matching base class.
    (see `Python Method Resolution Order`_ for more information on the
    ordering.)


.. _Python Method Resolution Order: https://www.python.org/download/releases/3.6/mro/

Stateful factory
^^^^^^^^^^^^^^^^

:py:meth:`~.DependencyManager.factory` can also be used to declare classes
as factories. It allows to keep some state between the calls.

For example when processing a request, the user is usually needed. It cannot be
a singleton as it may change at every request. But retrieving it from database
at every injection can be a performance hit. Thus the factory should at least
remember the current user.


.. testsetup:: advanced_usage

    class Database:
        def __init__(self, *args, **kwargs):
            pass

    class Request:
        def getSession(self):
            pass

    class User:
        pass


.. testcode:: advanced_usage

    from antidote import antidote
    # from database_vendor import Database
    # from web_framework import Request
    # from models import User

    @antidote.factory
    def database_factory() -> Database:
        return Database()

    @antidote.factory(singleton=False)
    def get_current_request() -> Request:
        return Request()

    @antidote.factory
    class UserFactory:
        def __init__(self, database: Database):
            self.database = database
            self.current_session = None
            self.current_user = None

        def __call__(self, request: Request) -> User:
            # No need to reload the user.
            if self.current_session != request.getSession():
                # load new user from database
                self.current_user = User()

            return self.current_user

    user = antidote.container[User]

This case is similar to what is called a scope in other dependency injection
framework. The same service may or may not be returned depending on some state.


Providers
---------

Overview
^^^^^^^^

More complex features are presented in this part, which relies on the
:ref:`api:Providers` which were not presented. Here is more accurate view
on how Antidote works::


                   +----------+                +-----------+
            +----> | Provider +--------------> | Container +------+
            |      +----------+                +-----------+      |
            |                      Provide                        |
            | Register                                            | Inject
            |                                                     v
            |
      +------------+                                         +----------+
      | Dependency |                                         | Function |
      +------------+                                         +----------+


The :py:class:`~.DependencyContainer` does not instantiate dependencies itself,
providers do. The container ensures among other things thread-safety and
caching of singletons. An important feature, is that one can pass additional
arguments to a provider with :py:class:`~.container.Dependency` to control how
a dependency is instantiated. For example with a factory, arguments can be
overriden:

.. testcode:: advanced_usage

    from antidote import antidote
    from operator import getitem

    class Database:
        """ Dummy Database """

        def __init__(self, host, user, password):
            self.host = host
            self.user = user
            self.password = password

    antidote.register_parameters(
        dict(host='host', user='user', password='pass'),
        getter=getitem,
        prefix='db_'
    )

    @antidote.factory(use_names=True)
    def db_factory(db_host, db_user, db_password) -> Database:
        return Database(db_host, db_user, db_password)

.. doctest:: advanced_usage

    >>> antidote.container[Database].host
    'host'
    >>> from antidote import Dependency as Dy
    >>> antidote.container[Dy(Database, db_host='new_host')].host
    'new_host'

How the additional arguments given through :py:class:`~.container.Dependency`
are used depends solely on the provider. Antidote has two providers by default:

- :py:class:`~.providers.FactoryProvider`: Handles dependencies which are
  created with a callable, such as dependencies registered through
  :py:meth:`~.DependencyManager.register` or
  :py:meth:`~.DependencyManager.factory`. Any additional arguments are passed
  on to the callable.
- :py:class:`~.providers.ParameterProvider`: Handles dependencies registered
  with :py:meth:`~.DependencyManager.register_parameters`. Any additional
  arguments are ignored.

Moreover it is possible to add providers with
:py:meth:`~.DependencyManager.provider`. However beware that the container
iterates over all the providers when it needs to instantiate a dependency. Thus
one should ensures that the dependencies provided by each provider are strictly
exclusive.

Accessing the providers
^^^^^^^^^^^^^^^^^^^^^^^

Providers are accessible through the dictionary
:py:attr:`~.DependencyContainer.providers` which contains them by their type.
For example you can access the
:py:class:`~.providers.factories.FactoryProvider` which manages all kind
of factories:

.. doctest:: advanced_usage

    >>> from antidote.providers import FactoryProvider
    >>> antidote.container.providers[FactoryProvider]
    FactoryProvider(...)

This allows you to create configurable providers, to be adapted across
projects for example.

Adding a provider
^^^^^^^^^^^^^^^^^

A provider should be used to customize how your dependencies are handled, for
example with a different cache. To define your own provider, you only need to
define a class with a method :code:`__antidote_provide__` accepting a first
argument a :py:class:`~.container.Dependency` and returning a
:py:class:`~.container.Instance`. If the dependency cannot be provided,
:py:exc:`~.exceptions.DependencyNotProvidableError` must be raised. The
following example presents a provider using a time limited cache:

.. testcode:: provider

    from antidote import (
        antidote, DependencyNotProvidableError, Dependency, Instance
    )
    import time

    @antidote.provider
    class TimeProvider:
        """ Caches instances only for the specified time. """
        def __init__(self):
            self._dependency_to_factory_and_ttl = {}
            self._cache = {}

        def __antidote_provide__(self, dependency: Dependency) -> Instance:
            try:
                factory, ttl = self._dependency_to_factory_and_ttl[dependency.id]
            except KeyError:
                raise DependencyNotProvidableError(dependency)

            try:
                instance, instantiated_at = self._cache[dependency.id]
            except KeyError:
                pass
            else:
                if (time.time() - instantiated_at) < ttl:
                    return instance

            instance = Instance(factory())
            self._cache[dependency.id] = (instance, time.time())

            return instance

        def register(self, dependency_id, factory, time_to_live=60):
            self._dependency_to_factory_and_ttl[dependency_id] = (
                factory,
                time_to_live
            )


.. doctest:: provider

    >>> def called_counter():
    ...     try:
    ...         called_counter.count += 1
    ...     except AttributeError:
    ...         called_counter.count = 1
    ...     return called_counter.count
    ...
    >>> antidote.providers[TimeProvider].register('test', called_counter,
    ...                                           time_to_live=1)
    >>> antidote.container['test']
    1
    >>> time.sleep(1)
    >>> antidote.container['test']
    2
