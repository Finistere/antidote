Defining dependencies
=====================


Antidote provides out of the box 4 different kinds of dependencies:

- :py:func:`.injectable` classes for which an instance is provided.
- :py:obj:`.const` for defining simple constants.
- :py:obj:`.lazy` function calls (taking into account arguments) used for (stateful-)factories, parameterized dependencies, complex constants, etc.
- :py:obj:`.interface` for a function, class or even :py:obj:`.lazy` function call for which one or multiple implementations can be provided.

Each Dependency has a lifetime defining how long :py:obj:`.world` holds their value alive. The most important are:

- :code:`singleton`: value is created at most once and re-used afterwards
- :code:`transient`: value is never cached and re-computed each time.

By default, all dependencies are :code:`singleton` but it can be easily changed:

.. testcode:: gs_3_lifetime

    from antidote import injectable, world

    @injectable(lifetime='transient')
    class SingleUse:
        pass

    assert world[SingleUse] is not world[SingleUse]

A third lifetime exist, :code:`scoped`, but its usage will presented later.


Injectable
----------

As shown multiple times before :py:func:`.injectable` defines a class as a dependency for which an instance of the said class will
be provided. By default, the decorated class will be automatically wired, like :py:func:`.wire`, with a :py:class:`.Wiring` that can be configured. It is
also possible to configure how the instance is created by specifying a :code:`factory_method`:

.. testcode:: gs_3_injectable

    from dataclasses import dataclass
    from antidote import injectable, world, inject

    @injectable
    class Service:
        pass

    @injectable(factory_method='load')
    @dataclass
    class ConfiguredService:
        config: object
        service: Service

        @classmethod
        def load(cls, service: Service = inject.me()) -> 'ConfiguredService':
            # load configuration from somewhere
            return cls(config='config', service=service)


.. doctest:: gs_3_injectable

    >>> world[ConfiguredService].config
    'config'
    >>> world[ConfiguredService].service is world[Service]
    True


Const
-----

:py:obj:`.const` defines either static constants or ones retrieved, lazily, from environment variables:

.. testcode:: gs_3_const

    from antidote import const, inject

    TMP_DIR = const("/tmp")

    # From environment variables
    LOCATION = const.env("PWD")
    USER = const.env()  # uses the name of the variable
    PORT = const.env(convert=int)  # convert the environment variable to a given type
    UNKNOWN = const.env(default='unknown')

    # A class provides a convenient namespace
    class Conf:
        TMP_DIR = const("/tmp")
        USER = const.env()

    @inject
    def f(tmp_dir: str = inject[Conf.TMP_DIR]) -> str:
        return tmp_dir

.. doctest:: gs_3_const

    >>> from antidote import world, inject
    >>> world[Conf.TMP_DIR]
    '/tmp'
    >>> world[UNKNOWN]
    'unknown'
    >>> import os
    >>> os.environ['PORT'] = '80'
    >>> world[PORT]
    80
    >>> f()
    '/tmp'


Lazy
----

:py:obj:`.lazy` defines a function *call* as a dependency. As such using the same arguments will
return the same dependency. By default, the decorated function will be injected with :py:obj:`.inject`.

.. testcode:: gs_3_lazy

    from antidote import lazy, world, inject, injectable

    @injectable
    class Service:
        pass

    @lazy
    def template(name: str, service: Service = inject.me()) -> str:
        return f"Template {name}"

    @inject
    def f(main_template = inject[template(name="main")]) -> str:
        return main_template

.. doctest:: gs_3_lazy

    >>> world[template(name="main")]
    'Template main'
    >>> f() is world[template(name="main")]  # singleton by default
    True

The original function can still be accessed through :code:`__wrapped__`. :py:obj:`.lazy` also
exposes several variations of itself:

- :py:meth:`~.Lazy.value` allows the function to be used like a variable:

    .. testcode:: gs_3_lazy_value

        from antidote import lazy

        class Redis:  # from another library, can't decorate with @injectable
            pass

        @lazy.value
        def app_redis() -> Redis:
            return Redis()

    .. doctest:: gs_3_lazy_value

        >>> from antidote import world
        >>> world[app_redis]
        <Redis object ...>

- :py:meth:`~.Lazy.method` will inject :code:`self` like :code:`@inject.method`. However, contrary
  to the latter it keeps the same behavior whether called from the class or an instance:

    .. testcode:: gs_3_lazy_method

        from dataclasses import dataclass
        from antidote import lazy, world, injectable

        @dataclass
        class Dummy:
            name: str

        @injectable
        @dataclass
        class Factory:
            prefix: str = 'Mr. '

            @lazy.method  # used as stateful factory
            def dummy(self, name: str) -> Dummy:
                return Dummy(name=f'{self.prefix}{name}')

    .. doctest:: gs_3_lazy_method

        >>> from antidote import world
        >>> world[Factory.dummy(name='John')]
        Dummy(name='Mr. John')
        >>> factory = Factory(prefix="Ms. ")
        >>> # calling from an instance does not change its behavior
        ... world[factory.dummy(name='John')]
        Dummy(name='Mr. John')

- :py:meth:`~.Lazy.property` behaves like a :py:class:`property` and will inject :code:`self`
  like :py:meth:`~.Lazy.method`:

    .. testcode:: gs_3_lazy_property

        from antidote import lazy, injectable

        @injectable
        class Conf:

            @lazy.property
            def host(self) -> str:
                return 'localhost'


    .. doctest:: gs_3_lazy_property

        >>> from antidote import world
        >>> world[Conf.host]
        'localhost'

To customize the injections, just apply :py:obj:`.inject` yourself:

.. testcode:: gs_3_lazy_custom_inject

    from antidote import lazy, inject, injectable

    @injectable
    class Service:
        pass

    @lazy
    @inject(kwargs=dict(service=Service))
    def f(service):
        ...

.. testcode:: gs_3_lazy_custom_inject
    :hide:

    from antidote import world
    world[f()]  # should not fail


Interface
---------

:py:obj:`.interface` defines a contract for which one or multiple implementations can be registered. The interface itself can be a class, a function or even a :py:obj:`.lazy` call. Implementations won't be directly accessible unless explicitly defined as such.

Class
^^^^^
For a class :py:class:`.implements` ensures that all implementations are subclasses of it.

.. testcode:: gs_defining_dependencies_interface_class

    from antidote import implements, inject, interface, world, instanceOf


    @interface
    class Task:
        pass


    @implements(Task)
    class CustomTask(Task):  # CustomTask must inherit Task
        pass


    assert world.get(CustomTask) is None  # CustomTask not directly accessible
    assert isinstance(world[Task], CustomTask)
    assert world[Task] is world[Task]  # CustomTask is a singleton

    # More on this latter, constraints can be passed down to single() and all() to filter implementations
    assert world[instanceOf(Task)] is world[Task]
    assert world[instanceOf(Task).single()] is world[Task]
    assert world[instanceOf(Task).all()] == [world[Task]]


    @inject
    def f(task: Task = inject.me()) -> Task:
        return task

    @inject  #   ⯆ Iterable[Task] / Sequence[Task] / List[Task] would also work
    def g(tasks: list[Task] = inject.me()) -> list[Task]:
        return tasks

    assert f() is world[Task]
    assert g() == world[instanceOf(Task).all()]


Underneath :py:class:`.implements uses :py:func:`.injectable`, so you can customize the implementation however you wish through it. The following implementation is strictly equivalent to the previous one:

.. testcode:: gs_defining_dependencies_interface_class

    from antidote import injectable

    @implements(Task)  #      ⯆ More on this later, this is what "hides" CustomTask
    @injectable(catalog=world.private)
    class CustomTask(Task):
        pass

"Hiding" the implementation is not a necessity though:

.. testcode:: gs_defining_dependencies_interface_class

    @implements(Task)
    @injectable  # not hidden anymore
    class CustomTask(Task):
        pass


When using a Protocol as an :py:obj:`.interface`, implementations will only be checked if :code:`runtime_checkable` was applied on the protocol. For proper static-typing alternative syntaxes are also provided:

.. testcode:: gs_defining_dependencies_interface_protocol

    from typing import Protocol, runtime_checkable

    from antidote import implements, interface, world, instanceOf


    @interface
    @runtime_checkable  # if present, implementations will be checked
    class Base(Protocol):
        def get(self) -> object:
            pass


    @implements.protocol[Base]()
    class BaseImpl:
        def get(self) -> object:
            pass


    assert isinstance(world[instanceOf[Base]], BaseImpl)


Function & Lazy
^^^^^^^^^^^^^^^
For a function :py:class:`.implements` ensures the signature of the implementation matches the interface.

.. testcode:: gs_defining_dependencies_interface_function

    from typing import Callable, List

    from antidote import implements, interface, world, inject


    @interface
    def validator(name: str) -> bool:
        ...

    @implements(validator)
    def not_too_long(name: str) -> bool:
        return len(name) < 10


    # returning the function itself
    assert world[validator] is not_too_long


    @implements(validator)
    def lower_case_only(name: str) -> bool:
        return name.lower() == name


    @inject
    def validate(name: str, validators: List[Callable[[str], bool]] = inject[validator.all()]) -> bool:
        return all(v(name) for v in validators)


    assert not validate("CAPITAL")
    assert not validate("this is too long to be validated")
    assert validate("antidote")

Like :py:obj:`.lazy`, it is also possible to define the function *call* as the dependency:

.. testcode:: gs_defining_dependencies_interface_lazy

    from antidote import implements, inject, interface, world


    @interface.lazy
    def template(name: str) -> str:
        ...


    @implements.lazy(template)
    def my_template(name: str) -> str:
        return f"My Template {name}"


    # Contrary to a function interface, here the template by itself is not a dependency.
    assert template not in world
    # Only the function call is
    assert world[template(name="world")] == "My Template world"
    # Retrieving a single implementation and calling it with specified arguments
    assert world[template.single()(name="world")] == "My Template world"


    @inject
    def f(world_template: str = inject[template(name="world")]) -> str:
        return world_template


    assert f() == "My Template world"

Similar to what we have seen for interface classes and :py:func:`.injectable`, :code:`@implements.lazy` applies :py:obj:`.lazy` underneath. The following is strictly equivalent to the previous definition:

.. testcode:: gs_defining_dependencies_interface_lazy

    from antidote import lazy

    @implements.lazy(template)
    @lazy(catalog=world.private)
    def my_template(name: str) -> str:
        return f"My Template {name}"


Multiple implementations
^^^^^^^^^^^^^^^^^^^^^^^^
Three different mechanisms exist to select one or multiple implementations among many. First let's define a simple interface:

.. testcode:: gs_defining_dependencies_interface_multiple_impl

    from antidote import interface

    @interface
    class CloudAPI:
        pass

1. At declaration, conditions define whether an implementation is registered or not:

.. testcode:: gs_defining_dependencies_interface_multiple_impl

    from antidote import inject, const, world, implements

    CLOUD = const('gcp')


    @inject
    def in_cloud(name: str, current_cloud: str = inject[CLOUD]) -> bool:
        return name == current_cloud


    @implements(CloudAPI).when(in_cloud('gcp'))
    class GCPapi(CloudAPI):
        pass


    @implements(CloudAPI).when(in_cloud('aws'))
    class AWSapi(CloudAPI):
        pass


    assert isinstance(world[CloudAPI], GCPapi)

2. A condition can also be a :py:class:`.Predicate` which allows adding metadata to an implementation. At request, it is then possible to filter implementations based on this metadata with a :py:class:`.PredicateConstraint`. Here is an example with the :py:class:`.QualifiedBy` predicate:


.. testsetup:: gs_defining_dependencies_interface_multiple_impl2

    from antidote import interface

    @interface
    class CloudAPI:
        pass

.. testcode:: gs_defining_dependencies_interface_multiple_impl2

    from antidote import world, implements, instanceOf, QualifiedBy


    @implements(CloudAPI).when(QualifiedBy('aws'))
    class AWSapi(CloudAPI):
        pass


    @implements(CloudAPI).when(qualified_by='gcp')  # shortcut definition
    class GCPapi(CloudAPI):
        pass


    assert isinstance(world[instanceOf(CloudAPI).single(qualified_by='aws')], AWSapi)

3. A condition not only defines whether an implementation is used or not, but also their ordering with an :py:class:`.ImplementationWeight`. By default the :py:class:`.NeutralWeight` is used, which as the name implies has no effect. It's possible to define one's own weight and use it in combination with the :py:class:`.NeutralWeight`, but two custom weight implementations cannot be used together:


.. testsetup:: gs_defining_dependencies_interface_multiple_impl3

    from antidote import interface

    @interface
    class CloudAPI:
        pass

.. testcode:: gs_defining_dependencies_interface_multiple_impl3

    from typing import Any
    from dataclasses import dataclass
    from antidote import world, implements, Predicate


    @dataclass
    class Weight:
        value: float

        @classmethod
        def neutral(cls) -> 'Weight':
            return Weight(0)

        @classmethod
        def of_neutral_predicate(cls, predicate: Predicate[Any]) -> 'Weight':
            return cls.neutral()

        def __lt__(self, other: 'Weight') -> bool:
            return self.value < other.value

        def __add__(self, other: 'Weight') -> 'Weight':
            return Weight(self.value + other.value)


    @implements(CloudAPI).when(Weight(1))
    class GCPapi(CloudAPI):
        pass


    @implements(CloudAPI)
    class AWSapi(CloudAPI):
        pass


    assert isinstance(world[CloudAPI], GCPapi)


Default implementation
^^^^^^^^^^^^^^^^^^^^^^
A default implementation is used whenever no alternative implementation can be used. You can either define it to be the interface itself or an implementation:

.. testcode:: gs_defining_dependencies_interface_default

    from antidote import interface, implements, world


    @interface.as_default
    def callback() -> None:
        pass


    assert world[callback] is callback.__wrapped__


    @implements(callback)
    def custom_callback() -> None:
        pass


    assert world[callback] is custom_callback


    @interface
    class Service:
        pass


    @implements(Service).as_default
    class ServiceDefaultImpl(Service):
        pass


    assert isinstance(world[Service], ServiceDefaultImpl)


    @implements(Service)
    class CustomServiceImpl(Service):
        pass


    assert isinstance(world[Service], CustomServiceImpl)


Overriding an implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
An (default) implementation can be overridden by another one. It'll be used in exactly the same
conditions as the original one.

.. testcode:: gs_defining_dependencies_interface_override

    from antidote import implements, interface, world


    @interface
    class Service:
        pass


    @implements(Service)
    class ServiceImpl(Service):
        pass


    @implements(Service).overriding(ServiceImpl)
    class Override(Service):
        pass


    assert isinstance(world[Service], Override)


Freezing dependencies definitions
---------------------------------

The catalog, :py:obj:`.world`, can be frozen in order to prevent any new dependency definitions with :code:`freeze()`, a :code:`FrozenCatalogError` will be raised instead:

.. testcode:: gs_freezing

    from antidote import world

    world.freeze()
