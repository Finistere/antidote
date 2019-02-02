Tutorial
========

This tutorial is a quick lesson on how to use Antidote features to write better
code. It is a series of steps to show what can be done easily.


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

    config = dict(url='my_url', env='PROD')

    def am_i_in_prod(env: str = None):
        env = env or config['env']
        return env == 'PROD'

Now we can call :code:`am_i_in_prod` without needing to be aware of what it
needs and are still able to test it properly with unit tests without having to
change the global configuration. The downside is that we have now a tight
coupling of the application code and the configuration. If your configuration
becomes more complicated, such as using environment variables to override some
parameters, you'll have to either adapt all functions like :code:`am_i_in_prod`
or create custom code to emulate your existing :code:`config`.

Let's give Antidote a shot and see what we can do:

.. testcode:: tutorial_conf

    from antidote import inject, world

    world.update_singletons(config)

    @inject(use_names=True)
    def am_i_in_prod_v2(env: str):
        return env == 'PROD'

.. doctest:: tutorial_conf

    >>> am_i_in_prod_v2()
    True
    >>> am_i_in_prod_v2('dev')
    False

Pretty easy ! We've updated the singletons stored in the global
:py:class:`.DependencyContainer` with the configuration directly.
For the injection we directly use the argument names by specifying
:code:`use_names=True`. Now while this feels a bit cleaner as  we don't pass
:code:`config` around anymore, changing how parameters are loaded in
:code:`config` is still the same.

To improve this, we have to define what Antidote calls a resource with the
decorator :py:func:`.resource`:

.. testcode:: tutorial_conf

    from antidote import resource

    @resource
    def conf(key):
        return config[key]

A resource is identified by a name, here :code:`key`, and a namespace. The
latter is implicit here, it's the functions name. The function itself is
expected to return the resource or to raise :py:exc:`LookupError` (which is the
base class for :py:exc:`KeyError` or :py:exc:`IndexError` for example). Once
declared, the resource can be accessed through its dependency ID
:code:`<namespace>:<name>` as in :

.. doctest:: tutorial_conf

    >>> world.get('conf:env')
    'PROD'

As we cannot have :code:`':'` in the argument name, we cannot use
:code:`use_names=True` anymore. We have to specify explicitly the mapping of
the arguments to their dependencies. That's what the parameter :code:`arg_map`
is for :

.. testcode:: tutorial_conf

    @inject(dependencies='conf:{arg_name}')
    def am_i_in_prod_v3(env: str):
        return env == 'PROD'

.. doctest:: tutorial_conf

    >>> am_i_in_prod_v3()
    True

Here a template string was used, which is syntactic sugar for :

.. testcode:: tutorial_conf

    @inject(dependencies=lambda name: 'conf:{}'.format(name))
    def am_i_in_prod_v4(env: str):
        return env == 'PROD'

.. note::

    :code:`arg_map` also accepts a sequence of dependency IDs, or a mapping:

    .. doctest:: tutorial_conf

        >>> @inject(dependencies=['conf:env'])
        ... def am_i_in_prod3(env: str):
        ...     return env == 'PROD'
        >>> @inject(dependencies=dict(env='conf:env'))
        ... def am_i_in_prod3(env: str):
        ...     return env == 'PROD'

    See :py:func:`.inject` for more information.

So what ares the pros of defining a resource ? It hides how you retrieve the
parameters from the code which is using them. Now you could retrieve parameters
with HTTP requests or through database queries and those would only be executed
only if they are necessary and once. Changing this would only affect the code
inside :code:`conf`, nothing else.

There is second advantage, multiple functions can declared for the same
resource:

.. testcode:: tutorial_conf

    from antidote import resource
    import os

    @resource(priority=10)
    def env_conf(name):
        return os.environ['APP_'.format(name.upper())]

    @resource
    def env_conf(name):
        return config[name.lower()]

    @inject(dependencies='env_conf:{arg_name}')
    def am_i_in_prod_v5(env: str):
        return env == 'PROD'

.. doctest:: tutorial_conf

    >>> am_i_in_prod_v5()
    True

A priority has to specified so Antidote knows which function it should call
first.

To summarize, declaring resources with Antidote helps decoupling the code,
which makes latter modification easier. Moreover using multiple endpoints to
retrieve configuration becomes obvious without any custom code which has to be
maintained.