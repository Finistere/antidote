Tutorial
========

This tutorial is a quick lesson on how to use Antidote features to write better
code. It is a series of steps to show what can be done easily. It will focus on
how to declare services and configuration. Note that Antidote can do a lot more
than presented here, don't hesitate to check out the


1. Overview
-----------

First of all, let's start with a quick example:

.. testcode:: tutorial_overview

    from antidote import inject, register

    @register
    class Service:
        pass

    @inject
    def f(service: Service):
        """ doing stuff here """
        return service


Now you can call the function :code:`f` without having to handle the creation
of the dependency :code:`Service` as it was registered before:

.. doctest:: tutorial_overview

    >>> f()
    <Service object at ...>

But you can still use :code:`f` like any other function:

.. doctest:: tutorial_overview

    >>> f(None)

If you need to retrieve :code:`Service` directly you can use the global
:py:class:`.DependencyContainer`:

.. doctest:: tutorial_overview

    >>> from antidote import world
    >>> world.get(Service)
    <Service object at ...>

By default, it will return same instance every time:

.. doctest:: tutorial_overview

    >>> world.get(Service) is world.get(Service)
    True

Let's take a quick look on how this works. It can be simplified to three
parts ::

                 +-----------+
          +----->| Container +------+
          |      +-----------+      |

     @register,...               @inject

          |                         |
          |                         v
    +-----+------+             +----------+
    | Dependency |             | Function |
    +------------+             +----------+

- a set of helper decorators such as :py:func:`.register` to define
  dependencies.
- a single container holding your dependencies
- :py:func:`.inject` which injects them into your function

In the next steps we will go through how Antidote can be used to inject
different kind of dependencies.


2. Services
-----------

A service is a class which provides some sort of functionality. A common one is
a class serving as an interface to a database:

.. testcode:: tutorial_services

    from antidote import inject, register

    @register
    class Database:
        def __init__(self):
            self.users = [dict(name='Bob')]

    @inject
    def get_user_count(db: Database):
        return len(db.users)

.. doctest:: tutorial_services

    >>> get_user_count()
    1

:py:func:`.inject` has automatically determined which dependency should be
injected based on the type hints. Antidote uses annotations as type hints and
nothing else. It is entirely compatible with tools like Mypy.

Dependencies are only injected when they have not been supplied to the
function. So you can write unit tests for the function easily:

.. doctest:: tutorial_services

    >>> get_user_count(Database())
    1

This works nicely, but what if we need other statistics ? Let's create a new
service for this:

.. testcode:: tutorial_services

    from antidote import register

    @register
    class DatabaseStatistics:
        def __init__(self, db: Database):
            self._db = db

        def get_user_count(self):
            return len(self._db.users)

.. doctest:: tutorial_services

    >>> from antidote import world
    >>> world.get(DatabaseStatistics).get_user_count()
    1

No need to use :py:func:`.inject` on :code:`__init__`, :py:func`.register` will
automatically inject any dependencies required by it. This is called
auto-wiring, and more complex behaviors is possible with the parameter
:code:`auto_wire`. Here :code:`auto_wire` is simply equal to :obj:`True`.

Statistics are great, but getting the first user would also be helpful. Let's
define its class first:

.. testcode:: tutorial_services

    class User:
        def __init__(self, name: str):
            self.name = name

        def __repr__(self):
            return 'User(name={!r})'.format(self.name)

Unfortunately :py:func:`.register` is not enough here, User does not know to
instantiate itself with the first user. But don't worry, Antidote has what we
need, a factory:

.. testcode:: tutorial_services

    from antidote import factory

    @factory
    def first_user(db: Database) -> User:
        return User(**db.users[0])

.. doctest:: tutorial_services

    >>> world.get(User)
    User(name='Bob')

:py:func:`factory` uses the return type hint as the dependency ID.

But what happens if we modify the database now ?

.. doctest:: tutorial_services

    >>> world.get(Database).users = [dict(name='Alice'), dict(name='John')]
    >>> get_user_count()
    2
    >>> world.get(DatabaseStatistics).get_user_count()
    2

Perfect ! What about our first user ?

.. doctest:: tutorial_services

    >>> world.get(User)
    User(name='Bob')

But... :code:`'Bob'` is not even in our database anymore ! We just missed an
important part of dependency injection, the scope of the dependency. The scope
is the context in which an specific instance is valid as a dependency. The
default scope is singleton, which means that dependencies are only instantiated
once during the application lifetime.

.. testcode:: tutorial_services

    class FirstUser:
        pass

    @factory(singleton=False)
    def first_user(db: Database) -> FirstUser:
        return User(**db.users[0])

.. doctest:: tutorial_services

    >>> world.get(FirstUser)
    User(name='Alice')

Here we created another type as Antidote does not accept any duplicate
dependency IDs.


3. Configuration
----------------

Every applications needs to load its configuration from somewhere, one simple
way to do this is to load a file into a global dictionary :code:`config` and
import it wherever necessary, like this:

.. testcode:: tutorial_conf

    config = dict(domain='example.com', port=3000)

    def absolute_url(path: str, domain: str = None, port: int = None):
        domain = domain or config['domain']
        port = port or config['port']
        return f"https://{domain}:{port}{path}"

Now we can call :code:`absolute_url` without needing to be aware of what it
needs and are still able to test it properly with unit tests without having to
change the global configuration. There are two major downsides here:

- we have now a tight coupling of the application code and the configuration
  as the inner body needs to know how to retrieve the configuration. If you need
  more complex parameters, from multiple sources or lazily loaded for example,
  you'll probably need to either adapt all functions like :code:`absolute_url`
  or create custom code to emulate your existing :code:`config`.
- Retrieving configuration through a string :code:`'domain'` makes refactoring
  more complicated, as your IDE cannot provide any support for refactoring.


Let's give Antidote a shot and see what we can do:

.. testcode:: tutorial_conf

    from antidote import LazyConstantsMeta, inject

    class Conf(metaclass=LazyConstantsMeta):
        DOMAIN = 'domain'
        PORT = 'port'

        def __init__(self):
            # Load anything you need and/or use dependencies.
            self._data = dict(domain='example.com', port=3000)

        def get(self, key):
            return self._data[key]

    @inject(dependencies=(None, Conf.DOMAIN, Conf.PORT))
    def absolute_url_v2(path: str, domain: str, port: int):
        return f"https://{domain}:{port}{path}"

.. doctest:: tutorial_conf

    >>> absolute_url_v2("/user/1")
    'https://example.com:3000/user/1'
    >>> absolute_url_v2('/dog/2', port=80)
    'https://example.com:80/dog/2'

Pretty easy ! Now you may think, that's a lot of code to access :code:`config`,
but it is much more flexible:

- :code:`Conf` has :code:`__init__()` and :code:`__call__()` injected, so you can
  rely on other dependencies easily.
- Everything is lazy, even the instantiation of :code:`Conf`.

:py:class:`.LazyConstantsMeta` accepts several parameters to customize its behavior:

.. testcode:: tutorial_conf

    from antidote import LazyConstantsMeta

    class CustomizedConf(metaclass=LazyConstantsMeta, lazy_method='__call__', auto_wire=False):
        DOMAIN = 'domain'
        PORT = 'port'

        def __init__(self):
            self._data = dict(domain='example.com', port=3000)

        def __call__(self, key):
            return self._data[key]

.. note::

    Only public uppercase class attributes will be converted to dependencies.
    This means that :code:`A` will be changed, but not :code:`_A` neither
    :code:`a`.
