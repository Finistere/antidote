Advanced Usage
==============

.. testsetup:: advanced_usage

    import antidote
    antidote.world['name'] = 'Antidote'


.. _advanced_usage_stateful_factory_label:

Registering a stateful factory
------------------------------

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

    import antidote
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

    user = antidote.world[User]

This case is similar to what is called a scope in other dependency injection
framework. The same service may or may not be returned depending on some state.


Customize the container with a provider
---------------------------------------

The :py:class:`~.DependencyContainer` does not instantiate the service itself,
it relies on providers to do so. If you need to handle a group of dependency
ids in a particular way, a provider is the way to go. To define your own
provider, you only need to define :code:`__antidote_provide__`:

.. testcode:: advanced_usage

    from antidote import DependencyNotProvidableError, Dependency

    @antidote.provider(use_names=True)
    class MyProvider:
        def __init__(self, name):
            self.name = name

        def __antidote_provide__(self, dependency_id):
            if dependency_id == 'whoami':
                return Dependency(self.name, singleton=False)

            raise DependencyNotProvidableError(dependency_id)

.. doctest:: advanced_usage

    >> antidote.world['whoami']
    'Antidote'

A dependency has to be returned wrapped in :py:class:
Note that it the dependency can not be instantiated, it has to raise
:py:exc:`~.DependencyNotProvidableError`.

.. note::

    Providers do not have to handle thread-safety themselves, this is done by
    the :py:class:`~.DependencyContainer`.


Accessing the providers
-----------------------

Providers are accessible through the dictionary
:py:attr:`~.DependencyContainer.providers` which contains them by their type.
For example you can access the
:py:class:`~.providers.factories.DependencyFactories` which manages all kind
of factories:

.. doctest:: advanced_usage

    >>> from antidote.providers import DependencyFactories
    >>> antidote.world.providers[DependencyFactories]
    <antidote.providers.factories.DependencyFactories object at ...>

This allows you to create configurable providers, to be adapted across
projects for example.
