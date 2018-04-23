Usage
=====


Overview
--------

Antidote can be simplified to a single container holding your dependencies and
two methods, :py:meth:`~.DependencyManager.register` and
:py:meth:`~.DependencyManager.inject` as the following figure presents ::

                 +-----------+
          +----->| Container +------+
          |      +-----------+      |

       Register                   Inject

          |                         |
          |                         v
    +-----+------+             +----------+
    | Dependency |             | Function |
    +------------+             +----------+

Registering a dependency makes it available for injection and directly
available from the container. There are multiple ways to register a dependency:

- :py:meth:`~.DependencyManager.register`: Register a class as a service. It'll
  be instantiated on demand.
- :py:meth:`~.DependencyManager.factory`: Register a factory which creates the
  dependency.
- :py:meth:`~.DependencyManager.register_parameters`: Register parameters, such
  as configuration.

:py:meth:`~.DependencyManager.inject` can be used on any function, injects
dependencies if and only if the arguments is not specified.


The container
-------------

The core component of Antidote is the :py:class:`~.DependencyContainer` which
builds dependencies upon request and caches them if possible. It behaves
closely like a dictionary:

.. doctest:: usage

    >>> from antidote import antidote
    >>> antidote.container['name'] = 'Antidote'
    >>> antidote.container['name']
    'Antidote'
    >>> antidote.container.update(dict(
    ...     some_parameter='some_parameter',
    ... ))
    >>> antidote.container['some_parameter']
    'some_parameter'

The key by which one can retrieve a dependency is called the *dependency id*
hereafter.

.. note::

    While you generally won't need to deal directly with it, it is extremely
    useful when testing as you can define and retrieve dynamically any
    dependency.


Register a dependency
---------------------

Services
^^^^^^^^

A service is a class which needs to be instantiated before injection.
Registering one is simply done by applying a decorator:

.. testcode:: usage

    @antidote.register
    class HelloWorld:
        def __init__(self):
            print("Building HelloWorld")

        def say_hi(self):
            print("Hi world !")

The class is used as the *dependency id*, so from now on you can retrieve it
from the :py:class:`~.DependencyContainer` with it:

.. doctest:: usage

    >>> my_hello_world = antidote.container[HelloWorld]
    Building HelloWorld
    >>> my_hello_world.say_hi()
    Hi world !

Note here that the instance is built lazily, only when requested. Should it be
never requested, it won't be instantiated.



Parameters (configuration)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Antidote can also inject constant parameters, which are usually defined in a
configuration object, such as a :py:class:`~configparser.ConfigParser` or a
nested dictionary. Antidote only need to know how to retrieve them from it:

.. testcode:: usage

    from operator import getitem

    config = {
        'date': {
            'year': '2017'
        }
    }

    antidote.register_parameters(config, getitem, prefix='conf:',
                                 split='.')

.. doctest:: usage

    >>> antidote.container['conf:date.year']
    '2017'

In the previous example additional arguments are used to customize how
Antidote should handle the *dependency id*. Specifying either :code:`prefix` or
:code:`split`, will make Antidote discard any *dependency id* that is not a
string.

- :code:`prefix`: The *dependency id* must begin with it. It will be removed
  for the :code:`getter`.
- :code:`split`: The *dependency id* into a list of keys used to recursively
  traverse the configuration object.

Factories
^^^^^^^^^

With complex services, or ones from libraries, you usually need a factory
to configure it correctly. Antidote provides the
:py:meth:`~.DependencyManager.factory` to do so.

Let's suppose you wish to register your favorite database client library which
provides a class :py:class:`Database` for your needs:

.. testcode:: usage

    class Database:
        def __init__(self, host, user, password):
            self.host = host
            self.user = user
            self.password = password

        def __repr__(self):
            return (
                "Database(host={host!r}, user={user!r}, "
                "password={password!r})"
            ).format(**vars(self))

The best way to handle such a case is to define the parameters in the container
and create a factory to instantiate the :py:class:`Database` class as a
service.

.. testcode:: usage

    from operator import getitem

    antidote.register_parameters(
        dict(
            host='localhost',
            user='admin',
            password='admin'
        ),
        getter=getitem,
        prefix="db_"
    )

    @antidote.factory(use_names=True)
    def database_factory(db_host, db_user, db_password) -> Database:
        return Database(
            host=db_host,
            user=db_user,
            password=db_password
        )

Now you can easily use the :py:class:`Database` service anywhere in your code:

.. doctest:: usage

    >>> antidote.container[Database]
    Database(host='localhost', user='admin', password='admin')

.. note::

    :ref:`usage:Complex Factories` presents more complex usage of
    factories such as instantiating subclasses or being stateful.

Singletons
^^^^^^^^^^

Services are by default singletons, and as such the container will always
return the same instance:

.. doctest:: usage

    >>> my_hello_world is antidote.container[HelloWorld]
    True

If you need the service to be built anew at each request, specify
:code:`singleton=False` to the decorator:

.. testcode:: usage

    @antidote.register(singleton=False)
    class NonSingletonService:
        def __init__(self):
            print("I'am new")

.. doctest:: usage

    >>> instance = antidote.container[NonSingletonService]
    I'am new
    >>> instance is antidote.container[NonSingletonService]
    I'am new
    False

Auto-wiring
^^^^^^^^^^^

Dependencies having often dependencies themselves, thus Antidote injects them
automatically. That is named "auto-wiring", as dependencies are wired together.
By default, :py:meth:`~.DependencyManager.register` will apply
:py:meth:`~.DependencyManager.inject` to the :code:`__init__` method of your
service. In order to customize injection, :code:`arg_map` and :code:`use_names`
can be used.

.. testcode:: usage

    @antidote.register(use_names=True)
    class Service:
        def __init__(self, name):
            self.name = name

.. doctest:: usage

    >>> service = antidote.container[Service]
    >>> service.name
    'Antidote'

With :py:meth:`~.DependencyManager.factory`,
:py:meth:`~.DependencyManager.inject` will be applied on the factory itself.

.. note::

    Auto-wiring offers additional functionalities, presented in
    :ref:`usage:Custom auto-wiring`.

Inject a dependency
-------------------

Decorator
^^^^^^^^^

Injection is as simple as it gets with the
:py:meth:`~.DependencyManager.inject` decorator:

.. doctest:: usage

    >>> @antidote.inject
    ... def speak(my_hello_world: HelloWorld):
    ...     my_hello_world.say_hi()
    ...
    >>> speak()
    Hi world !

Antidote relies foremost on type annotations to inject necessary dependencies
into your function. However those are often not adequate, for configuration
parameters for example. For such cases, two additional arguments can be
specified:

- :code:`use_names`: A list of arguments for which their names should be used
  as their respective *dependency*. Specifying :code:`True` will apply this for
  all arguments. This overrides any annotations.

  .. doctest:: usage

      >>> @antidote.inject(use_names=True)
      ... def whoami(name: HelloWorld):
      ...     print("Name: {}".format(name))
      ...
      >>> whoami()
      Name: Antidote
      >>> antidote.container['my_hello_world'] = None
      >>> @antidote.inject(use_names=['name'])
      ... def whoami(name: str, my_hello_world: HelloWorld):
      ...     my_hello_world.say_hi()
      ...     print("Name: {}".format(name))
      ...
      >>> whoami()
      Hi world !
      Name: Antidote

- :code:`arg_map`: A list of *dependency ids* which is mapped to the arguments
  by their ordering or dictionary mapping arguments name to their dependencies.
  This overrides annotations and :code:`use_names`.

  .. doctest:: usage

      >>> @antidote.inject(arg_map=('conf:date.year', HelloWorld))
      ... def which_args(year, my_hello_world):
      ...     my_hello_world.say_hi()
      ...     print("Year: {}".format(year))
      ...
      >>> which_args()
      Hi world !
      Year: 2017
      >>> @antidote.inject(arg_map=dict(year='conf:date.year'))
      ... def which_args(year):
      ...     print("Year: {}".format(year))
      ...
      >>> which_args()
      Year: 2017

Furthermore as Antidote aims to be easy to integrate with existing code, one
can still call an injected function like before with its argument or part of
them:

.. doctest:: usage


    >>> @antidote.inject(arg_map=['conf:date.year'], use_names=True)
    ... def whoami(year, name):
    ...     print("{}: {}".format(year, name))
    ...
    >>> whoami()
    2017: Antidote
    >>> whoami(2001, "A Space Odyssey")
    2001: A Space Odyssey
    >>> whoami(name="Will you stop, Dave? Stop, Dave. I'm afraid.",
    ...        year="HAL")
    HAL: Will you stop, Dave? Stop, Dave. I'm afraid.


.. note::

    Dependency mapping of the arguments to their respective dependency is done
    at the first execution to limit the injection overhead. However, the
    retrieval of those is done at each execution.

    If execution speed matters, one can use :code:`bind=True` to inject the
    dependencies at import time. A :py:func:`functools.partial` is then used to
    bind the arguments. However, if your function is called thousands of times
    in a loop, you should avoid injection.

    Check out the `injection benchmark <https://github.com/Finistere/antidote/blob/master/benchmark.ipynb>`_
    for numbers.

Attrs
^^^^^

Antidote provides also support for the
`attr <http://www.attrs.org/en/stable>`_ package (version >= 17.1). As
usual you have multiple ways to map the dependency to the attribute:

- Variable annotation for Python 3.6+
- Name of the attribute
- Explicit *dependency id*.

.. testcode:: usage

    import attr

    @attr.s
    class MyClass:
        name = antidote.attrib(use_name=True)
        custom_dependency = antidote.attrib('my_hello_world')

Internally antidote uses a :py:class:`attr.Factory` and any additional keyword
argument is passed on to it.


Mocking
-------

When testing your application one usually need to change the dependencies or
control which one are accessible. This can be easily done with the
:py:meth:`~.DependencyManager.context` context manager:

.. doctest:: usage

    >>> antidote.container['param'] = 1
    >>> with antidote.context(dependencies={'param': 2}):
    ...     print(antidote.container['param'])
    2
    >>> with antidote.context(include=[]):
    ...     antidote.container['param']
    Traceback (most recent call last):
     ...
    antidote.exceptions.DependencyNotFoundError: param


Advanced
--------

.. testsetup:: advanced_usage

    from antidote import antidote
    antidote.container['name'] = 'Antidote'

Custom auto-wiring
^^^^^^^^^^^^^^^^^^

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
if applied on a class (see :ref:`usage:Using a class as a factory`).

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


Complex Factories
^^^^^^^^^^^^^^^^^

Subclasses Instantiation
""""""""""""""""""""""""

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

Using a class as a factory
""""""""""""""""""""""""""

:py:meth:`~.DependencyManager.factory` can also be used to declare classes
as factories. It allows you to keep some state between the calls.

For example when processing a request, the user is usually needed. It cannot be
a singleton as it may change at every request. But retrieving it from database
at every injection is a performance hit. Thus the factory should at least
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
