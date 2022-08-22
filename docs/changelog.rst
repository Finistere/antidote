*********
Changelog
*********


For any given version :code:`N`, all releases :code:`N.X.X` guarantee:

- API stability: Python code that used to work will continue work.
- Namespace stability for :code:`antidote` and :code:`antidote.core`. Other namespaces are susceptible to changes.
- *best effort* for static type hints stability. Meaning that code relying on Antidote that used to pass MyPy
  or any other static type checker should continue working, but it's best effort.

Most, if not all, of the API is annotated with decorators such as :code:`@API.public` specifying whether
the given functionality can be relied upon.



2.0.0 (2022-08-31)
====================

Antidote core has been entirely reworked to be simpler and provide better static typing in addition
of several features. The cython had to be dropped though for now by lack of time. It may eventually
come back.


Breaking Changes
----------------

Important
^^^^^^^^^
- All previously deprecated changes have been removed.
- The previous :code:`Scope` concept has been replaced by :py:class:`.LifeTime` and :py:class:`.ScopeGlobalVar`.
- :code:`world.test` environments API have been reworked. Creating one has a similar API and guarantees, but :code:`world.test.factory`, :code:`world.test.singleton` and all of :code:`world.test.override` have been replaced by a better alternative. See :py:class:`.TestContextBuilder`.
- Dependencies cannot be specified through :code:`inject({...})` and :code:`inject([...])` anymore.
- :py:class:`.QualifiedBy`/:code:`qualified_by` for interface/implementation now relies on equality instead of the :code:`id()`.
- :py:obj:`.const` API has been reworked. :code:`const()` and :code:`cont.env()` have API changes and :code:`const.provider` has been removed.
- Thread-safety guarantees from Antidote are now simplified. It now only ensures lifetime consistency and some decorators such as :py:func:`.injectable` & :py:obj:`.interface` provide some thread-safety guarantees.
- :py:class:`.Provider` has been entirely reworked. It keeps the same name and purpose but has a different API and guarantees.

Core
^^^^
- :py:obj:`.inject`
    - removed :code:`dependencies`, :code:`strict_validation` and :code:`auto_provide` parameters.
    - removed :code:`source` parameter from :py:meth:`.Inject.me`
- :py:class:`.Wiring`
    - removed :code:`dependencies` parameter.
    - renamed :code:`class_in_localns` parameter to :code:`class_in_locals` in :py:meth:`.Wiring.wire`.
- :py:func:`.wire`: removed :code:`dependencies` parameter 
- renamed :code:`Get` to :code:`dependencyOf`. Usage of :code:`inject[]`/:code:`inject.get` is recommended instead for annotations.
- :py:obj:`.world`
    - Providers are not dependencies anymore. Use :py:attr:`.Catalog.providers`.
    - Providers do not check anymore that a dependency wasn't defined by another one before. They're expected to be independent.
    - Exception during dependency retrieval are not wrapped in :code:`DependencyInstantiationError` anymore
    - :code:`FrozenWorldError` has been renamed :code:`FrozenCatalogError`.
    - :code:`world.test.new()` now generates a test environment equivalent to a freshly created Catalog with :code:`new_catalog`. It only impacts those using a custom :code:`Provider`.
    - Removed dependency cycle detection and :code:`DependencyCycleError`. It wasn't perfectly accurate and it's not really worth it. :code:`world.debug` does a better job at detecting and presenting those cycles.
- :code:`validate_injection()` and :code:`validated_scope()` functions have been removed.
- :code:`DependencyGetter`, :code:`TypedDependencyGetter` are not part of the API anymore.

Injectable
^^^^^^^^^^
- The first argument :code:`klass` of :py:func:`.injectable` is now positional-only.
- :code:`singleton` and :code:`scope` parameters have been replaced by :code:`lifetime`.

Interface
^^^^^^^^^
- :code:`ImplementationsOf` has been renamed to :py:class:`.instanceOf`.
- :py:class:`.PredicateConstraint` protocol is now a callable instead of having an :code:`evaluate()` method.
- Classes wrapped by :py:class:`.implements` are now part of the private catalog by default, if you want them to be available, you'll need to apply :py:func:`.injectable` explicitly.
- :py:meth:`.implements.overriding` raises a :py:exc:`ValueError` instead of :py:exc:`RuntimeError` if the implementation does not exist.
- The default implementation is now only provided if no other implementations matched. It wasn't the case with :code:`all()` before.
- :code:`implements.by_default` has been renamed to :py:meth:`.implements.as_default` to be symmetrical with :py:obj:`.interface`.

Lazy
^^^^
- :code:`singleton` and :code:`scope` parameters have been replaced by :code:`lifetime`.
- :code:`call()` function was removed from lazy functions, use the :code:`__wrapped__` attribute instead.
- In test contexts such as :code:`world.test.empty()` and :code:`world.test.new()`, previously defined lazy/const dependencies will not be available anymore.

Const
^^^^^
- To specify a type for :py:meth:`.Const.env` use the :code:`convert` argument.
- When defining static constant values such as :code:`HOST = const('localhost')`, it's NOT possible to:

    - define the type (:code:`const[str]('localhost)`)
    - define a default value
    - not provide value at all anymore

- :code:`const.provider` has been removed. Use :py:meth:`.Lazy.method` instead. The only difference is that the const provider would return different objects even with the same arguments, while the lazy method won't.


Features
--------

Core
^^^^
-   AEP1: Instead of hack of module/functions :py:obj:`.world` is now a proper instance of  :py:obj:`.PublicCatalog`. Alternative catalogs can be created and included in one another. Dependencies can also now be private or public. The main goal is for now to expose a whole group of dependencies through a custom catalog.

    .. code-block:: python

        from antidote import new_catalog, inject, injectable, world

        # Includes by default all of Antidote
        catalog = new_catalog()


        # Only accessible from providers by default.
        @injectable(catalog=catalog.private)
        class PrivateDummy:
            ...


        @injectable(catalog=catalog)  # if catalog is not specified, world is used.
        class Dummy:
            def __init__(self, private_dummy: PrivateDummy = inject.me()) -> None:
                self.private_dummy = private_dummy


        # Not directly accessible
        assert PrivateDummy not in catalog
        assert isinstance(catalog[Dummy], Dummy)


        # app_catalog is propagated downwards for all @inject that don't specify it.
        @inject(app_catalog=catalog)
        def f(dummy: Dummy = inject.me()) -> Dummy:
            return dummy


        assert f() is catalog[Dummy]

        # Not inside world yet
        assert Dummy not in world
        world.include(catalog)
        assert world[Dummy] is catalog[Dummy]

-   AEP2 (reworked): Antidote now defines a :py:class:`.ScopeGlobalVar` which has a similar interface to :py:class:`ContextVar` and three kind of lifetimes to replace scopes:

        - :code:`'singleton'`: instantiated only once
        - :code:`'transient'`: instantiated on every request
        - :code:`'scoped'`: used by dependencies depending on one or multiple :py:class:`.ScopeGlobalVar`. When any of them changes, the value is re-computed otherwise it's cached.

    :py:class:`.ScopeGlobalVar` isn't a :py:class:`ContextVar` though, it's a global variable. It's planned to add a :py:class:`.ScopeContextVar`.

    .. code-block:: python

        from antidote import inject, lazy, ScopeGlobalVar, world

        counter = ScopeGlobalVar(default=0)

        # Until update, the value stays the same.
        assert world[counter] == 0
        assert world[counter] == 0
        token = counter.set(1)
        assert world[counter] == 1


        @lazy(lifetime='scoped')
        def dummy(count: int = inject[counter]) -> str:
            return f"Version {count}"


        # dummy will not be re-computed until counter changes.
        assert world[dummy()] == 'Version 1'
        assert world[dummy()] == 'Version 1'
        counter.reset(token)  # same interface as ContextVar
        assert world[dummy()] == 'Version 0'

-   Catalogs, such as :py:obj:`.world` and :py:obj:`.inject`, expose a dict-like read-only API. Typing has also been improved:

    .. code-block:: python

        from typing import Optional

        from antidote import const, inject, injectable, world


        class Conf:
            HOST = const('localhost')
            STATIC = 1


        assert Conf.HOST in world
        assert Conf.STATIC not in world
        assert world[Conf.HOST] == 'localhost'
        assert world.get(Conf.HOST) == 'localhost'
        assert world.get(Conf.STATIC) is None
        assert world.get(Conf.STATIC, default=12) == 12

        try:
            world[Conf.STATIC]
        except KeyError:
            pass


        @injectable
        class Dummy:
            pass


        assert isinstance(world[Dummy], Dummy)
        assert isinstance(world.get(Dummy), Dummy)


        @inject
        def f(host: str = inject[Conf.HOST]) -> str:
            return host


        @inject
        def g(host: Optional[int] = inject.get(Conf.STATIC)) -> Optional[int]:
            return host


        assert f() == 'localhost'
        assert g() is None

-   Testing has a simplified dict-like write-only API:

    .. code-block:: python

        from antidote import world

        with world.test.new() as overrides:
            # add a singleton / override existing dependency
            overrides['hello'] = 'world'
            # add multiple singletons
            overrides.update({'second': object()})
            # delete a dependency
            del overrides['x']


            # add a factory
            @overrides.factory('greeting')
            def build() -> str:
                return "Hello!"

-   Added :py:meth:`.Inject.method` which will inject the first argument, commonly :code:`self` of a method with the dependency defined by the class. It won't inject when used as instance method though.

    .. code-block:: python

        from antidote import inject, injectable, world


        @injectable
        class Dummy:
            @inject.method
            def method(self) -> 'Dummy':
                return self


        assert Dummy.method() is world[Dummy]
        dummy = Dummy()
        assert dummy.method() is dummy

-   :py:obj:`.inject` now supports wrapping function with :code:`*args`.
-   :py:obj:`.inject` has now :code:`kwargs` and :code:`fallback` keywords to replace the old :code:`dependencies`. :code:`kwargs` takes priority over alternative injections styles and :code:`fallback` is used in the same way as :code:`dependencies`, after defaults and type hints.


Interface
^^^^^^^^^
-   :py:obj:`.interface` now supports function and :py:obj:`.lazy` calls. It also supports defining the interface as the default function with :py:meth:`.Interface.as_default`:

    .. code-block:: python

        from antidote import interface, world, implements


        @interface
        def callback(x: int) -> int:
            ...


        @implements(callback)
        def callback_impl(x: int) -> int:
            return x * 2


        assert world[callback] is callback_impl
        assert world[callback.single()] is callback_impl


        @interface.lazy.as_default
        def template(name: str) -> str:
            return f"Template {name!r}"


        assert world[template(name='test')] == "Template 'test'"


        @implements.lazy(template)
        def template_impl(name: str) -> str:
            return f"Alternative template {name!r}"


        assert world[template.all()(name='root')] == ["Alternative template 'root'"]

-   Better API for :py:class:`~typing.Protocol` static typing:

    .. code-block:: python

        from typing import Protocol

        from antidote import implements, instanceOf, interface, world


        @interface
        class Dummy(Protocol):
            ...


        @implements.protocol[Dummy]()
        class MyDummy:
            ...


        assert isinstance(world[instanceOf[Dummy]()], MyDummy)
        assert isinstance(world[instanceOf[Dummy]().single()], MyDummy)

-   :py:class:`.QualifiedBy` relies on equality instead of the id of the objects now. Limitations on the type of qualifiers has also been removed.

    .. code-block:: python

        from antidote import implements, interface


        @interface
        class Dummy:
            ...


        @implements(Dummy).when(qualified_by='a')
        class A(Dummy):
            ...


        @implements(Dummy).when(qualified_by='b')
        class B(Dummy):
            ...

-   :py:class:`.implements` has a :code:`wiring` argument to prevent any wiring.

Lazy
^^^^
- :py:obj:`.lazy` can now wrap (static-)methods and define values/properties:

    .. code-block:: python

        from antidote import injectable, lazy, world


        @lazy.value
        def name() -> str:
            return "John"


        @injectable  # required for lazy.property & lazy.method
        class Templates:
            @lazy.property
            def main(self) -> str:
                return "Lazy Main Template"

            @lazy.method
            def load(self, name: str) -> name:  # has access to self
                return f"Lazy Method Template {name}"

            @staticmethod
            @lazy
            def static_load(name: str) -> str:
                return f"Lazy Static Template {name}"


        world[name]
        world[Templates.main]
        world[Templates.load(name='Alice')]
        world[Templates.static_load(name='Bob')]

-   :py:obj:`.lazy` has now an :code:`inject` argument which can be used to prevent any injection.



1.4.2 (2022-06-26)
==================


Bug fix
-------

- Fix injection error for some union type hints such as :code:`str | List[str]`.



1.4.1 (2022-06-01)
==================


Bug fix
-------

- Fix type error for :py:meth:`.implements.overriding`.



1.4.0 (2022-05-22)
==================


Deprecation
-----------

- :py:class:`.Constants` is deprecated as not necessary anymore with the new :py:obj:`.const`.
- :py:func:`~.factory.factory` is deprecated in favor of :py:func:`.lazy`.


Features
--------

- :py:func:`.lazy` has been added to replace :py:func:`~.factory.factory` and the
  :code:`parameterized()` methods of both :py:class:`.Factory` and :py:class:`.Service`.

  .. code-block:: python

      from antidote import lazy, inject

      class Redis:
          pass

      @lazy  # singleton by default
      def load_redis() -> Redis:
          return Redis()

      @inject
      def task(redis = load_redis()):
          ...

- :py:obj:`.const` has been entirely reworked for better typing and ease of use:

  - it doesn't require :py:class:`.Constants` anymore.
  - environment variables are supported out of the box with :py:meth:`.Const.env`.
  - custom logic for retrieval can be defined with :py:meth:`.Const.provider`.

  Here's a rough overview:

  .. code-block:: python

      from typing import Optional, TypeVar, Type

      from antidote import const, injectable

      T = TypeVar('T')

      class Conf:
          THREADS = const(12)  # static const
          PORT = const.env[int]()  # converted to int automatically
          HOST = const.env("HOSTNAME")  # define environment variable name explicitly,


      @injectable
      class Conf2:
          # stateful factory. It can also be stateless outside of Conf2.
          @const.provider
          def get(self, name: str, arg: Optional[str]) -> str:
              return arg or name

          DUMMY = get.const()
          NUMBER = get.const[int]("90")  # value will be 90

- :py:meth:`.implements.overriding` overrides an existing implementation, and will be used in
  exactly the same conditions as the overridden one: default or not, predicates...
- :py:meth:`.implements.by_default` defines a default implementation for an interface outside of
  the weight system.


Experimental
------------

- :py:meth:`.ConstantValueProvider.converter` provides a similar to feature to the legacy
  :code:`auto_cast` from :py:class:`.Constants`.


Bug fix
-------

- Better behavior of :py:obj:`.inject` and :py:func:`.world.debug` with function wrappers, having a
  :code:`__wrapped__` attribute.



1.3.0 (2022-04-26)
==================


Deprecation
-----------

- :py:func:`.service` is deprecated in favor of :py:func:`.injectable` which is a drop-in
  replacement.
- :py:func:`.inject` used to raise a :py:exc:`RuntimeError` when specifying
  :code:`ignore_type_hints=True` and no injections were found. It now raises
  :py:exc:`.NoInjectionsFoundError`
- :py:meth:`.Wiring.wire` used to return the wired class, it won't be the case anymore.


Features
--------

- Add local type hint support with :code:`type_hints_locals` argument for :py:func:`.inject`,
  :py:func:`.injectable`, :py:class:`.implements` and :py:func:`.wire`. The default behavior can
  be configured globally with :py:obj:`.config`. Auto-detection is done through :py:mod:`inspect`
  and frame manipulation. It's mostly helpful inside tests.

  .. code-block:: python

      from __future__ import annotations

      from antidote import config, inject, injectable, world


      def function() -> None:
          @injectable
          class Dummy:
              pass

          @inject(type_hints_locals='auto')
          def f(dummy: Dummy = inject.me()) -> Dummy:
              return dummy

          assert f() is world.get(Dummy)


      function()

      config.auto_detect_type_hints_locals = True


      def function2() -> None:
          @injectable
          class Dummy:
              pass

          @inject
          def f(dummy: Dummy = inject.me()) -> Dummy:
              return dummy

          assert f() is world.get(Dummy)


      function2()

- Add :code:`factory_method` to :py:func:`.injectable` (previous :py:func:`.service`)

  .. code-block:: python

      from __future__ import annotations

      from antidote import injectable


      @injectable(factory_method='build')
      class Dummy:
          @classmethod
          def build(cls) -> Dummy:
              return cls()

- Added :code:`ignore_type_hints` argument to :py:class:`.Wiring` and :py:func:`.wire`.
- Added :code:`type_hints_locals` and :code:`class_in_localns` argument to :py:class:`.Wiring.wire`.


Bug fix
-------

- Fix :code:`Optional` detection in predicate constraints.



1.2.0 (2022-04-19)
==================


Bug fix
-------

- Fix injection error when using the :code:`Klass | None` notation instead of :code:`Optional[Klass]`
  in Python 3.10.


Features
--------

- :code:`frozen` keyword argument to :py:func:`.world.test.clone` which allows one to control
  whether the cloned world is already frozen or not.
- Both :code:`inject.get` and :code:`world.get` now strictly follow the same API.
- :py:func:`.interface` and py:class:`implements` which provide a cleaner way to separate
  implementations from the public interface. Qualifiers are also supported out of the box. They
  can be added with :code:`qualified_by` keyword and requested with either :code:`qualified_by` or
  :code:`qualified_by_one_of`.

    .. code-block:: python

        from antidote import implements, inject, interface, world, QualifiedBy

        V1 = object()
        V2 = object()


        @interface
        class Service:
            pass


        @implements(Service).when(qualified_by=V1)
        class ServiceImpl(Service):
            pass


        @implements(Service).when(QualifiedBy(V2))
        class ServiceImplV2(Service):
            pass


        world.get[Service].single(qualified_by=V1)
        world.get[Service].all()


        @inject
        def f(service: Service = inject.me(QualifiedBy(V2))) -> Service:
            return service


        @inject
        def f(services: list[Service] = inject.me(qualified_by=[V1, V2])) -> list[Service]:
            return services



Experimental
------------

- :py:class:`.Predicate` API is experimental allows you to define your custom logic
  for selecting the right implementation for a given interface. Qualifiers are implemented with
  the :py:class:`.QualifiedBy` predicate which is part of the public API.




1.1.1 (2022-03-25)
==================


Bug fix
-------

- Injected functions/methods with :py:func:`.inject` did not behave correctly with
  :code:`inspect.isfunction`, :code:`inspect.ismethod`, :code:`inspect.iscoroutinefunction`
  and :code:`inspect.iscoroutine`.



1.1.0 (2022-03-19)
==================


Breaking static typing change
-----------------------------

- A function decorated with :py:func:`~.factory.factory` will not have the :code:`@` operator
  anymore from a static typing perspective. It's unfortunately not possible with the addition of
  the class support for the decorator.


Deprecation
-----------

- :py:class:`.Service` and :py:class:`.ABCService` are deprecated in favor of :py:func:`.service`.
- Passing a function to the argument :code:`dependencies` of :py:func:`.inject` is deprecated.
  If you want to customize how Antidote injects dependencies, just wrap :py:func:`.inject` instead.
- :py:func:`.inject`'s :code:`auto_provide` argument is deprecated. If you rely on this behavior,
  wrap :py:func:`.inject`.
- :code:`world.lazy` is deprecated. It never brought a lot of value, one can easily write it oneself.
- :code:`dependency @ factory` and :code:`dependency @ implementation` are replaced by the more explicit
  notation:

  .. code-block:: python

    world.get(dependency, source=factory)

    @inject(dependencies={'db': Get(dependency, source=factory)})
    def (db):
        ...

- Annotation :code:`Provide` has been renamed :code:`Inject`.
- :code:`world.get` will not support extracting annotated dependencies anymore.
- Omitting the dependency when a type is specified in :code:`world.get` is deprecated. :code:`world.get`
  provides now better type information.

  .. code-block:: python

    from antidote import world, service

    @service
    class Dummy:
        pass

    # this will expose the correct type:
    world.get(Dummy)

    # so this is deprecated
    world.get[Dummy]()

    # you can still specify the type explicitly
    world.get[Dummy](Dummy)


Change
------

- Both :code:`world.get` and :code:`const` have better type checking behavior, doing it only when
  the specified type is an actual instance of :code:`type`. For protocols, type check will only
  be done with those decorated with :code:`@typing.runtime_checkable`.
- Dropped Python 3.6 support.


Features
--------

- Add :code:`ignore_type_hints` to :py:func:`.inject` to support cases when type hints cannot be
  evaluated, typically in circular imports.
- Adding Markers for :py:func:`.inject` used as default arguments to declare injections:

  .. code-block:: python

    from antidote import const, Constants, factory, inject, service


    class Config(Constants):
        HOST = const[str]("host")


    @service
    class Dummy:
        value: str


    @factory
    def dummy_factory() -> Dummy:
        return Dummy()


    # inject type hint
    @inject
    def f(dummy: Dummy = inject.me()) -> Dummy:
        return dummy


    # inject type hint with factory
    @inject
    def f2(dummy: Dummy = inject.me(source=dummy_factory)) -> Dummy:
        return dummy


    # inject constants
    @inject
    def f3(host: str = Config.HOST) -> str:
        return host


    # inject a dependency explicitly
    @inject
    def f4(x=inject.get(Dummy)) -> Dummy:
        return x


    # inject a dependency with a factory explicitly
    @inject
    def f5(x=inject.get(Dummy, source=dummy_factory)) -> Dummy:
        return x



1.0.1 (2021-11-06)
==================


Change
------

- Update :code:`fastrlock` dependency to :code:`>=0.7,<0.9` to support Python 3.10 for the compiled
  version.



1.0.0 (2021-04-29)
==================

No changes. From now on breaking changes will be avoided as much as possible.



0.14.2 (2021-04-28)
===================


Features
--------

- Added :code:`wiring` argument to :py:func:`.service` and auto-wiring like :py:class:`.Service`.



0.14.1 (2021-04-25)
===================


Features
--------

- Added :py:class:`.ABCService` for services to be easier to work with ABC abstract classes.
- Added support for a function in :code:`auto_provide`



0.14.0 (2021-03-30)
===================


Breaking Change
---------------

- :code:`LazyDependency` and :code:`WithWiringMixin` are not part of the public API anymore.
  For the first just use :py:obj:`.world.lazy` instead, and the later was experimental.
- :py:func:`.world.scopes.new` argument :code:`name` is keyword-only now.



0.13.0 (2021-03-24)
===================


Breaking Change
---------------

- :code:`_with_kwargs()` class method has been replaced by :py:meth:`.Service.parameterized` and
  :py:meth:`.Factory.parameterized` with a cleaner design. Now parameters must be explicitly
  defined in their respective configuration. Those will be verified to ensure they don't have
  any injections or default values, as sanity checks. Otherwise passing the default value as a
  parameter or relying on the actual default would not point to the same dependency value.



0.12.1 (2021-03-07)
===================


Change
------

- Improved :py:func:`.world.test.clone` performance to be as fast as possible to avoid
  any overhead in tests in the compiled version.



0.12.0 (2021-02-06)
===================


Feature / Breaking Change
-------------------------

- Add runtime type checks when a type is explicitly defined with :py:obj:`.world.get`,
  :py:obj:`.world.lazy` or :py:class:`.Constants`.



0.11.0 (2021-02-05)
===================


Features
--------

- Add scope support.
- Add annotated type hints support (PEP-593).
- Add async injection support.
- Multiple factories can be defined for the same class.
- Cleaner testing support, by separating explicitly the case where test existing
  dependencies or want to create new ones.
- All methods of :py:class:`.Service`, :py:class:`.Factory` and :py:class:`.Constants`
  are automatically wired to support annotated type hints anywhere.


Breaking changes
----------------

- Remove :code:`public` configuration for :py:class:`.Factory` and :py:class:`.Constants`.
  They didn't really bring any value, you hardly hide anything in Python.
- Removed tags. They didn't bring enough value.
- Reworked :py:func:`.inject`: it will only inject annotated type, nothing else anymore.
  :code:`use_type_hint` has been replaced by :code:`auto_provide` and :code:`use_names`
  has been removed.
- Reworked :py:class:`.Constants` to be more flexible.
- Removed :code:`world.singletons`. There was no way to track back where a singleton
  was defined.
- Reworked :py:class:`.Wiring` to be simpler, not super class wiring



0.10.0 (2020-12-24)
===================


Breaking change
---------------

- In :py:class:`.Wiring`, :code:`ignore_missing_methods` has been replaced by
  :code:`attempt_methods`.


Bug fix
-------

- Using :py:meth:`.inject` on :code:`__init__()` of a :py:class:`.Service`, or any methods
  injected by default by Antidote, will not raise a double injection error anymore.



0.9.0 (2020-12-23)
==================


Features
--------

- Antidote exposes its type information (PEP 561) and passes strict Mypy (with implicit optionals).


Breaking changes
----------------

- Antidote exceptions have no public attributes anymore.
- Injecting twice the same function/method will raise an error.
- :py:class:`.Constants` has been simplified, :py:obj:`.const` is now simply always required
  to define a constant.


Changes
-------

- Better, simpler :code:`DependencyInstantiationError` when a deeply nested dependency fails.
- Cleaner packaging: Antidote will only try to compile Cython when the environment variable
  :code:`ANTIDOTE_COMPILED` is set to :code:`true` and doesn't require Cython to be pre-installed
  to do so. Antidote's version is also hardcoded at publish time.
- Added a Scope example in the documentation. It is a bit more complicated than I would like,
  but scopes are hard



0.8.0 (2020-12-09)
==================


Features
--------

- Reworked entirely :code:`world`:
    - Cleaner singletons declarations in :py:mod:`.world.singletons`
    - Test utilities in :py:mod:`.world.test`. Those allow you to change locally, withing a
      context manager, dependencies declarations. Hence you can replace an existing
      dependency by a mock for example.
    - Override utilities in :py:mod:`.world.test.override` to be used in tests.
    - Debug utility :py:func:`.world.debug` which returns a tree of all the dependencies
      that will/may be retrieved by Antidote.
    - Add type hints to :py:obj:`.world.get` which can now be used like :code:`world.get[<class>]("x")`
    - Add :py:obj:`.world.lazy` for dependencies to retrieve dependencies lazily.
- :py:func:`.implementation` is more flexible than :code:`@implements` and supports changing the
  implementation at runtime for example.
- :py:class:`.Service` and :py:class:`.Factory` expose a handy class method
  :py:meth:`~.Service.with_kwargs` which allows you to specify some key word argument to
  customize the service you're retrieving. Typically you would have only one database
  service class but use this feature to have two different dependencies which each point to
  different database.
- :py:class:`.Constants`, formerly :code:`LazyConstantsMeta`, supports a new of defining constants:
  :py:obj:`.const`. It has two purposes, explicitly define constants and optionally specify
  the actual type.
- Added :py:func:`.world.freeze` which will prevent any new dependencies to be added.


Breaking changes
----------------

- Drop support of Python 3.5.
- Singletons do check for duplicates now. Hence one cannot redefine an existing singleton
  through :code:`world`.
- :code:`world.update_singletons` does not exists anymore, use :py:func:`.world.test.singleton_all` or
  :py:func:`.world.test.singleton` instead.
- :code:`@register` is now replaced by the class :py:class:`.Service` and provides mostly the same
  features. The only corner cases are service that used factories, those should now
  really use a factory, namely :py:class:`.Factory` or :py:class:`.factory`. If you cannot
  inherit the super class for some reason, you may fallback to the class decorator
  :py:func:`.service`.
- :code:`@factory` for functions behaves the same way, however for factory classes the super
  class :py:class:`.Factory` must be used. The dependency identifier has also been to changed,
  the factory must now be specified like :code:`dependency @ factory` instead of :code:`dependency`.
- :code:`LazyConstantsMeta` has been replaced by the class :py:class:`.Constants`. One cannot
  choose the lazy method anymore, but it is more flexible regarding definition of constants.
- :code:`@implements` has been entirely reworked and split into :py:func:`.implementation` and
  :py:class:`.Implementation`. The latter can be used for straightforward cases where only
  one implementation exists. The first lets you handle all other cases with multiple
  implementations which can vary during runtime or not.
- :code:`@provider` has been replaced by the class decorator :py:func:`.world.provider`.
- Everything related to the container management has been removed for the public interface.


Changes
-------

- Add Python 3.9 support.
- public APIs are clearly defined as such, marked by :code:`@API.public`. Overall public API
  is also better defined.
- Improved Cython performance



0.7.2 (2020-04-21)
==================


Bug fixes
---------

- The wrapper of the injection function didn't behave exactly like a proxy for the 
  all of the wrapped functions attributes. Furthermore the Cython version didn't 
  support setting dynamically attributes at all.



0.7.0 (2020-01-15)
==================


Breaking changes
----------------

- :code:`@register` does not wire :code:`__init__()` anymore if a function is provided as a factory.
  This didn't make a lot of sense, :code:`__init__()` is wrapped automatically if and only if
  it is treated as the "factory" that creates the object.
- Now when using :code:`dependencies` argument with a sequence (matching dependencies with arguments
  through their position), the first argument will be ignored for methods (`self`) and 
  classmethod (`cls`). So now you can write:

  .. code-block:: python

      from antidote import inject, service

      class Service:
          @inject(dependencies=('dependency',))
          def method(self, arg1):
              ...

          @inject(dependencies=('dependency',))
          @classmethod
          def method(cls, arg1):
              ...

      @service(dependencies=('dependency',))
      class Service2:
          def __init__(self, arg1):
              ...

  Hence all other decorators profit from this. No need anymore to explicitly ignore :code:`self`.


Bug fixes
---------

- Prevent double :code:`LazyMethodCall` wrapping in :code:`LazyConstantsMeta` (Thanks @keelerm84)
- :code:`@inject` cannot be applied on classes. This was never intended as it would not
  return a class. Use :code:`@wire` instead if you relied on this.
- :code:`@inject` returned :code:`ValueError` instead of :code:`TypeError` in with erroneous types.
- :code:`@register` now raises an error when using a method as a factory that is neither a
  classmethod nor a staticmethod. It was never intended to use methods, as it would not
  make sense.


Changes
-------

- When wrapping multiple methods, :code:`@wire` used to raise an error if a sequence was
  provided for :code:`dependencies`. This limitation has been removed.



0.6.1 (2019-12-01)
==================


- Add support for Python 3.8



0.6.0 (2019-05-06)
==================


Features
--------

- Add :code:`@implements` to define service implementing an interface.
- Add :code:`IndirectProvider()` which supports :code:`@implements`.
- Add :code:`Container.safe_provide()` which does the same as
  :code:`Container.provide()` except that it raises an error if
  the dependency cannot be found instead of returning None.


Breaking changes
----------------

- :code:`Container.provide()` returns a :code:`DependencyInstance` not the
  instance itself anymore.
- Rename :code:`LazyConfigurationMeta` to :code:`LazyConstantsMeta`.
- :code:`LazyConfigurationMeta` default method is :code:`get()`.
- :code:`ServiceProvider` renamed to :code:`FactoryProvider` and reworked
  :code:`ServiceProvider.register()` with is split into :code:`register_factory()`,
  :code:`register_class`, :code:`register_providable_factory`.


Changes
-------

- Moved :code:`is_compiled` to :code:`antidote.utils`.
- Add better type hints.



0.5.1 (2019-04-27)
==================


Features
--------

- Add :code:`is_compiled()` to check whether the current version is compiled or pure
  python.



0.5.0 (2019-04-27)
==================


Breaking changes
----------------

- :code:`@resource` has been removed an replaced by :code:`LazyConfigurationMeta` to handle
  configuration. 


Features
--------

- Add :code:`LazyMethodCall` and :code:`LazyCall` to support output of functions as dependencies.


Changes
-------

- Add better type hints for helper decorators.



0.4.0 (2019-02-03)
==================


A lot of internals have changed, but it can roughly be resumed as the following:


Breaking changes
----------------

- The :code:`DependencyManager` does not exist anymore and has been replaced by
  multiple helpers which accepts a :code:`container` argument. By default the global
  container of Antidote is used. Thus one can easily replace 
  :code:`from antidote import antidote` to :code:`import antidote` to adapt existing code.
- The global container of Antidote, previously named :code:`container`, has been
  renamed :code:`world`.
- :code:`Dependency` does not take additional arguments anymore, for custom
  dependencies :code:`Build`, :code:`Tagged` must be used instead.
- Custom providers must inherit :code:`Provider`.
- :code:`register_parameters()` has been replaced by a more general function,
  :code:`resource()`. See the documentation to imitate its functionality.
- :code:`factory()` is more strict. Subclasses are not handled anymore, one should
  use :code:`register()` with its :code:`factory` argument instead.


Features
--------

- Dependencies can be tagged at registration. Those can then be retrieved as
  a dependency. This allows one to extend an app by registering a service in
  special way just by adding a tag.
- Type hints usage can now be finely controlled or disabled with :code:`use_type_hints`.
- Add :code:`resource()` to support custom resources, such as configuration.
- Dependency providers are more strict for more maintainable code.
- Use of Cython for better injection performance.



0.3.0 (2018-04-29)
==================


Initial release
