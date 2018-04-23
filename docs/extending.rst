Extending
=========


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

.. testcode:: extending

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

.. doctest:: extending

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

.. doctest:: extending

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
                # Is instance too old ?
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
    ...     """ Counts the number of times it was called. """
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
    >>> time.sleep(.1)
    >>> antidote.container['test']
    1
    >>> time.sleep(1)
    >>> antidote.container['test']
    2
