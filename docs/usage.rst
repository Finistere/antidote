Usage
=====


Container
---------

All dependencies are stored in the :py:class:`~.DependencyContainer` which
instantiates them lazily.

.. testsetup:: container
    .. code-block:: python

    from antidote import antidote

    class Database:
        def __init__(self, *args, **kwargs):
            pass

    antidote.container.register(Database)


.. testcode:: container
    .. code-block:: python

    from antidote import antidote
    # from database_vendor import Database

    # Services can be retrieved with their dependency_id (usually their type)
    database = antidote.container[Database]

    # Dependencies can also be defined directly
    antidote.container['database'] = Database()


Extending
^^^^^^^^^

The :py:class:`~.DependencyContainer` can be easily extended with additional
dependencies through :py:meth:`~.DependencyContainer.extend`. Those are used
if no dependency registered could be found.

.. testcode:: container
    .. code-block:: python

    from antidote import antidote

    antidote.container.extend(dict(
        database_host='host',
        database_user='user',
        database_password='password',
    ))

.. note::

    The container does not need to be extended by a dictionary, any object with
    :code:`__getitem__()` defined can be used.


Override
^^^^^^^^

Dependencies previously defined can be overridden either by setting it directly
or using :py:meth:`~.DependencyContainer.override`.

.. testcode:: container
    .. code-block:: python

    from antidote import antidote

    old_database = antidote.container[Database]

    antidote.container[Database] = Database()

    assert old_database is not antidote.container[Database]

    antidote.container.override({Database: Database()})


Registration
------------


Dependencies can be registered either through the
:py:meth:`~.DependencyManager.factory` or the
:py:meth:`~.DependencyManager.register` decorators.
:ref:`usage-register-auto-wiring-label` is enabled by default to automatically
inject the dependencies of a newly registered one.


Services
^^^^^^^^

:py:meth:`~.DependencyManager.register` declares a class as a services at
its definition:

.. testcode::
    .. code-block:: python

    from antidote import antidote

    @antidote.register
    class MyService:
        """ Custom service code """

    # Retrieving your service
    my_service = antidote.container[MyService]

.. note::

    All the defined dependencies lies in the global
    :py:class:`.DependencyContainer` and thus can be accessed directly as shown
    in the previous example.

However, one usually not always defines the service himself and uses an existing
class from libraries for external services like databases. In such cases, it is
recommended to deactivate :ref:`auto-wiring <usage-register-auto-wiring-label>`
with :code:`auto_wiring=False` as annotations have no constraints and thus may
lead to erroneous injections.

.. testsetup:: register_external_database
    .. code-block:: python

    class Database:
        def __init__(self, *args, **kwargs):
            pass


.. testcode:: register_external_database
    .. code-block:: python

    from antidote import antidote
    # from database_vendor import Database

    # Register the class directly, it will be instantiated when necessary.
    antidote.register(Database, auto_wire=False)




Factories
^^^^^^^^^

As its name clearly states, :py:meth:`~.DependencyManager.factory` should be
used to declare factories.

In the previous example, no configuration can be passed on safely to the
:code:`Database`. However, a factory can be created for which dependencies can
be injected. Using :code:`use_arg_name=True` provides easier configuration
retrieval as the arguments name will be used as dependency ids.

.. testsetup:: user_external_database
    .. code-block:: python

    from antidote import antidote

    antidote.container.update(dict(
        database_host='host',
        database_user='user',
        database_password='password',
    ))

    class Database:
        def __init__(self, *args, **kwargs):
            pass

    @antidote.register
    class Request:
        def getSession(self):
            pass

    class User:
        pass

.. testcode:: user_external_database
    .. code-block:: python

    from antidote import antidote
    # from database_vendor import Database

    # Variables names will be used for injection.
    @antidote.factory(use_arg_name=True)
    def database_factory(database_host, database_user, database_password) -> Database:
        return Database(
            host=database_host,
            user=database_user,
            password=database_password
        )

But :py:meth:`~.DependencyManager.factory` can also be used to declare classes
as factories. It allows to keep some state between the calls. For example when
processing a request, the user is usually needed. It cannot be a singleton as
it may change at every request. But retrieving it from database at every
injection can be a performance hit. Thus the factory should at least remember
the current user. A custom cache could also be used to remember frequently
requested dependencies.


.. testcode:: user_external_database
    .. code-block:: python

    from antidote import antidote
    # from database_vendor import Database
    # from web_framework import Request
    # from models import User

    @antidote.factory
    class UserFactory:
        def __init__(self, database: Database):
            self.database = database
            self.current_session = None
            self.current_user = None

        def __call__(self, request: Request) -> User:
            # No need to reload the user.
            if self.current_session != request.getSession():
                self.current_user = object() # load new user from database

            return self.current_user

    user = antidote.container[User]

.. _usage-register-auto-wiring-label:

Auto-wiring
^^^^^^^^^^^

When registering a service or a factory, its dependencies are automatically
injected. The wiring is done by the :py:class:`.DependencyManager`, hence the
option :code:`auto_wire`. By default :py:meth:`~.DependencyManager.register`
wires :code:`__init__()`. :py:meth:`~.DependencyManager.factory` also wires
:code:`__call__()` which can be used to inject non-singleton dependencies.

The auto-wiring may also be used directly to inject similar dependencies to
multiple methods with :py:meth:`~.DependencyManager.wire`. The user retrieval
could so look like:

.. testcode:: user_external_database
    .. code-block:: python

    from antidote import antidote
    # from database_vendor import Database
    # from web_framework import Request

    @antidote.wire(methods=('__init__', 'getUser'))
    class UserManager:
        def __init__(self, db: Database):
            pass

        def getUser(self, request: Request):
            pass

    # Retrieving the current user.
    user_manager = UserManager()
    user = user_manager.getUser()


Additional methods can be wired in the registration by specifying the methods
name :code:`auto_wire=('__init__', 'some_method')`

Hooks
^^^^^

A factory may need to be used for multiple services, typically to instantiate
subclasses. As those are not known at registration, it needs to be done at
service retrieval with a :code:`hook`.

.. testcode::
    .. code-block:: python

    from antidote import antidote

    class Service:
        pass

    class SubService(Service):
        pass

    @antidote.factory(hook=lambda id: issubclass(id, Service))
    def service_factory(service_id) -> Service:
        return service_id()

    sub_service = antidote.container[SubService]

Injection
---------

Injecting dependencies is simply done through the
:py:meth:`~.DependencyManager.inject` decorator. Three ways are supported to
define the dependencies, in order:

1. Mapping of the arguments name to their dependencies specified with
   :code:`mapping` argument.
2. Argument annotations.
3. Arguments name if :code:`use_arg_name=True` is specified.

Dependencies are used like default arguments: if the function is called with
all its arguments nothing is injected. A :py:exc:`DependencyNotFoundError` is
only raised when the argument has not default.


.. testsetup:: injection
    .. code-block:: python

    from antidote import antidote

    @antidote.register
    class Database:
        def __init__(self, *args, **kwargs):
            pass

    antidote.container.update(dict(
        database_host='host',
        database_user='user',
        database_password='password',
    ))

.. testcode:: injection
    .. code-block:: python

    from antidote import antidote
    # from database_vendor import Database

    @antidote.inject
    def get_users(db: Database):
        # do some stuff
        pass

    get_users()

    @antidote.inject(use_arg_name=True)
    def new_db(database_host, database_user, database_password):
        pass

    new_db()
    new_db('another_host')
    new_db(database_user='another user', database_password='password')

Dependency mapping of the arguments to their respective dependency is done at
the first execution to limit the injection overhead. However, the retrieval
of those is done at each execution, which allows dependencies to be changed.

If execution speed matters, one can use :code:`bind=True` to inject the
dependencies at import time. A :py:func:`functools.partial` is then used to
bind the arguments.

.. testcode:: injection
    .. code-block:: python

    from antidote import antidote
    # from database_vendor import Database

    @antidote.inject(bind=True)
    def get_users(db: Database):
        # do some stuff
        pass

    @antidote.inject(use_arg_name=True, bind=True)
    def new_db(database_host, database_user, database_password):
        pass


Further
--------


Scopes
^^^^^^


Configuration
^^^^^^^^^^^^^


Dynamic injection
^^^^^^^^^^^^^^^^^
Store data, keep reference to which code has generated it. async / sync