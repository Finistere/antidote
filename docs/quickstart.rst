Quickstart
==========

This page presents simple examples to get started quickly.


The container
-------------

The core component of Antidote is the :py:class:`~.DependencyContainer` which
contains dependencies by their *dependency id* and behaves like a
dictionary:

.. doctest:: quickstart

    >>> from antidote import antidote
    >>> antidote.container['name'] = 'Antidote'
    >>> antidote.container['name']
    'Antidote'
    >>> antidote.container.update(dict(
    ...     some_parameter='some_parameter',
    ... ))
    >>> antidote.container['some_parameter']
    'some_parameter'

It can be used to either retrieve a specific service or to define parameters
typically.


Register a service
------------------

Registering services with Antidote is very simple, just add the
:py:meth:`~.DependencyManager.register` decorator. The class itself will be
used as the *dependency id* for the service.

.. testcode:: quickstart

    @antidote.register
    class HelloWorld:
        def say_hi(self):
            print("Hi world !")

Now you can retrieve it from the :py:class:`~.DependencyContainer`:

.. doctest:: quickstart

    >>> my_hello_world = antidote.container[HelloWorld]
    >>> my_hello_world.say_hi()
    Hi world !


Register parameters (config)
----------------------------

One usually has some configuration in the form of a :py:class:`configparser.ConfigParser`
or as a nested dictionary. To enable Antidote to retrieve data from those, a
parser is needed to transform a dependency ID to a key. As keys are usually
strings, antidote provides a shortcut to define the parser.


.. testcode:: quickstart

    config = {
        'date': {
            'year': '2017'
        }
    }

    antidote.register_parameters(config, getter='rgetitem', prefix='conf:')

.. doctest:: quickstart

    >>> antidote.container['conf:date.year']
    '2017'

For more complex cases, :py:meth:`~.DependencyManager.register_parameters` also
accepts custom parsers:


.. testcode:: quickstart

    @antidote.register_parameters(config)
    def parser(params, dependency_id):
        if dependency_id == 'conf:date.year':
            return params['date']['year']

        raise LookUpError(dependency_id)

Custom parsers must return a sequence of keys, which are used to recursively
retrieve the value from the configuration. If the dependency ID is not a valid
key, :py:obj:`None` can be returned.


.. note::

    If you need a parameter to be casted to another type, you have to use
    :py:class:`~.container.Prepare`:

    .. doctest:: quickstart

            >>> from antidote import Prepare
            >>> antidote.container[Prepare('conf:date.year', coerce=int)]
            2017

        For more information on this, check out :ref:`Prepare <passing_parameter_with_prepare>`

Inject a dependency
-------------------

Injection is as simple as it gets, just use the
:py:meth:`~.DependencyManager.inject` decorator:

.. doctest:: quickstart

    >>> @antidote.inject
    ... def speak(my_hello_world: HelloWorld):
    ...     my_hello_world.say_hi()
    ...
    >>> speak()
    Hi world !

And you can still call to :py:func:`speak` with its argument:

.. doctest:: quickstart

    >>> class HelloWorldAndBye(HelloWorld):
    ...     def say_hi(self):
    ...         super(HelloWorldAndBye, self).say_hi()
    ...         print("Bye !")
    ...
    >>> speak(HelloWorldAndBye())
    Hi world !
    Bye !
    >>> speak(my_hello_world=HelloWorldAndBye())
    Hi world !
    Bye !

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


Inject without annotations
--------------------------

Sometimes you cannot use annotations to specify the dependencies, for
configuration parameters or if you are stuck with Python 2 (poor
soul) for example.

In this case you can use the arguments name instead of the type hint to search
in the :py:class:`~.DependencyContainer` :

.. doctest:: quickstart

    >>> @antidote.inject(use_names=True)
    ... def whoami(name):
    ...     print(name)
    ...
    >>> whoami()
    Antidote

If you need to restrict it to only some arguments you can simply specify those:

.. doctest:: quickstart

    >>> antidote.container['born_in'] = 2017
    >>> @antidote.inject(use_names=('name',))
    ... def present_me(name, born_in=None):
    ...     print("I'm {}".format(name))
    ...     if born_in:
    ...         print("Born in {}".format(born_in))
    ...
    >>> present_me()
    I'm Antidote
    >>> @antidote.inject(use_names=('name', 'born_in'))
    ... def present_me(name, born_in=None):
    ...     print("I'm {}".format(name))
    ...     if born_in:
    ...         print("Born in {}".format(born_in))
    ...
    >>> present_me()
    I'm Antidote
    Born in 2017

As last resort, if neither the name nor type hints can be used, you can
specify the dependencies explicitly with :code:`arg_map`:

.. doctest:: quickstart

    >>> @antidote.inject(arg_map={'my_hello_world': HelloWorld})
    ... def hi(my_hello_world):
    ...     my_hello_world.say_hi()
    ...
    >>> hi()
    Hi world !

:code:`arg_map` can also be a sequence of dependencies. Those are directly
mapped to the arguments with their order:

.. doctest:: quickstart

    >>> @antidote.inject(arg_map=(HelloWorld,))
    ... def hi_v2(my_hello_world):
    ...     my_hello_world.say_hi()
    ...
    >>> hi_v2()
    Hi world !

.. note::

    Antidote tries to find the matching dependency id, in order, from:

    1. mapping
    2. type hints
    3. argument name

    If no dependency could be found and the argument has no default value,
    :py:exc:`~.DependencyNotFoundError` will be raised at execution.


Auto-wiring
-----------

Often a service has its own dependencies, which themselves need to be injected.
That is what auto-wiring does, injecting dependencies of a dependency. Antidote
does it automatically when registering a service:

.. testcode:: quickstart

    @antidote.register(use_names=True)
    class Service:
        def __init__(self, name):
            self.name = name

.. doctest:: quickstart

    >>> service = antidote.container[Service]
    >>> service.name
    'Antidote'

:py:meth:`~.DependencyManager.register` accepts :code:`use_names` and
:code:`arg_map` parameters with the same meaning as those from
:py:meth:`~.DependencyManager.inject`. By default only :code:`__init__()` is
injected. :py:meth:`~.DependencyManager.factory` also wires :code:`__call__()`
if applied on a class (to create
:ref:`stateful factories <advanced_usage_stateful_factory_label>`).

If you need to wire multiples methods, you only need to specify them:

.. testcode:: quickstart

    @antidote.register(use_names=True, auto_wire=('__init__', 'get'))
    class Service:
        def __init__(self, name):
            self.name = name

        def get(self, name):
            return name

.. doctest:: quickstart

    >>> service = antidote.container[Service]
    >>> service.get()
    'Antidote'

Auto-wiring can also be deactivated if necessary:

.. testcode:: quickstart

    @antidote.register(auto_wire=False)
    class BrokenService:
        def __init__(self, name):
            self.name = name

.. doctest:: quickstart

    >>> service = antidote.container[BrokenService]
    Traceback (most recent call last):
        ...
    antidote.exceptions.DependencyInstantiationError: <class 'BrokenService'>


Non singleton service
---------------------

By default, all services are declared as singletons:

.. doctest:: quickstart

    >>> service = antidote.container[Service]
    >>> service is antidote.container[Service]
    True

While this is usually the expected behavior, as the service is only
instantiated once, you may need to always get a *new* instance.

.. testcode:: quickstart

    @antidote.register(singleton=False)
    class NonSingletonService:
        pass

.. doctest:: quickstart

    >>> service = antidote.container[NonSingletonService]
    >>> service is antidote.container[NonSingletonService]
    False


Register factory
----------------

With complex services, or ones from libraries, you usually need a factory
to configure it correctly. Antidote provides the
:py:meth:`~.DependencyManager.factory` to do so.

Let's suppose you wish to register your favorite database client library which
provides a class :py:class:`Database` for your needs:

.. testcode:: quickstart

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

.. testcode:: quickstart

    antidote.container.update(dict(
        host='localhost',
        user='admin',
        password='admin'
    ))

    @antidote.factory(use_names=True)
    def database_factory(host, user, password) -> Database:
        return Database(
            host=host,
            user=user,
            password=password
        )

Now you can easily use the :py:class:`Database` service anywhere in your code:

.. doctest:: quickstart

    >>> antidote.container[Database]
    Database(host='localhost', user='admin', password='admin')


Use a factory for subclasses
----------------------------

A factory handling subclasses is a common pattern, thus it is made easy to do
so by using the parameter :code:`build_subclasses`:

.. testcode:: quickstart

    class Service:
        def __init__(self, name):
            self.name = name

    class SubService(Service):
        pass

    @antidote.factory(build_subclasses=True, use_names=True)
    def service_factory(cls, name) -> Service:
        return cls(name)

.. doctest:: quickstart

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


.. _Python Method Resolution Order: https://www.python.org/download/releases/2.3/mro/
