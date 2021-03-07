**************************
Frequently Asked Questions
**************************



Why dependency injection ?
==========================


Dependency injection is a form of inversion of control. In short you're not creating/retrieving a
service by hand, you're *asking* for it. Instead of:

.. testcode:: why_dependency_injection

    from typing import Any

    class Database:
        def query(self, sql: str) -> Any:
            pass

    def get_total_count() -> int:
        db = Database()
        return db.query("SELECT COUNT(*) FROM my_table")

    get_total_count()

You do:

.. testcode:: why_dependency_injection

    def get_total_count(db: Database) -> int:
        return db.query("SELECT COUNT(*) FROM my_table")

    get_total_count(Database())

Here :code:`get_total_count()` doesn't rely directly on the class :code:`Database` anymore. It only expects
to be given an object that exposes the same interface, a method :code:`query(sql: str) -> Any`.
This leads to more **modular code** as there less coupling between :code:`get_total_count()` and :code:`Database`.
In the later you can change how :code:`Database` must be created without changing :code:`get_total_count()`. It
also leads to **easier testing**, you only need to prove an object that behaves the same way, no need
to know how :code:`Database` actually works.

Now in simple projects, you would just have an instance of :code:`Database` in a module and give it to the functions that needs it.

.. testcode:: why_dependency_injection

    # services.py
    db = Database()

.. code-block:: python

    # main.py
    from services import db
    get_total_count(db)

But as your project grows, you'll have more and more dependencies leading to complex code for the sole purpose of managing them.
That's what Antidote solves for you. You don't have to manage dependencies, you just need to declare how it should be managed
and where it should be injected:

.. testcode:: why_dependency_injection

    from antidote import Service, inject, Provide

    class Database(Service):
        def query(self, sql: str) -> Any:
            pass

    @inject
    def get_total_count(db: Provide[Database]) -> int:
        return db.query("SELECT COUNT(*) FROM my_table")

    get_total_count()



Why use a dependency injection framework ?
==========================================


Based on the previous example, let's suppose you don't always need the database. Instantiating it takes times, so you
want to avoid it if possible. A simple way to do

.. testcode:: why_dependency_injection

    # services.py
    from typing import Optional

    __db: Optional[Database] = None

    def get_db() -> Database:
        global __db
        if __db is None:
            __db = Database()
        return __db

That's still fine to maintain. But how does :code:`Database` know where the database is ? This needs configuration:

.. testcode:: why_dependency_injection

    # config.py

    class Config:
        pass

.. testcode:: why_dependency_injection

    # services.py
    __db: Optional[Database] = None

    config = Config()

    def get_db(host: str, port: int) -> Database:
        global __db
        if __db is None:
            __db = Database(host, port)
        return __db

Now it starts to get complicated. How should the :code:`config` be handled ? With the above you need to have access
the :code:`config` to be able to retrieve the :code:`Database` because host and port must be given. So you have a global
object that you carry everywhere. You could use :code:`config` inside the :code:`get_db()` but that breaks dependency
injection. Is it that bad ? It can quickly become cumbersome in tests, you have to manage a global state used by your
code. Starts to get really ugly, but kinda manageable.

But what if the configuration isn't coming from a file but it's stored in the Database / on a remote server ? This starts
to get really complex. Now imagine if you have tens of services: templating engine, database, AWS s3 storage,
other micro-services with which you communicate, APIs of clients/data sources etc..

Now that you write all your custom code, is it maintainable ? Will a newcomer easily find where a service is coming
from / how it's defined ? Is it easy to override in tests ?

That's where Antidote shines, it handles all of it for you in a simple, yet maintainable way. So you worry less on how
to do all that wiring properly. Here is the same example with Antidote:

.. testcode:: why_dependency_injection


    from antidote import Service, inject, Provide, Constants, const

    class Config(Constants):
        DB_HOST = const('localhost')
        DB_PORT = const(5432)

    class Database(Service):
        @inject([Config.DB_HOST, Config.DB_PORT])
        def __init__(self, host: str, port: int):
            pass

        def query(self, sql: str) -> Any:
            pass

    @inject
    def get_total_count(db: Provide[Database]) -> int:
        return db.query("SELECT COUNT(*) FROM my_table")

    get_total_count()

Everything is lazily instantiated, only when necessary. You can easily find where the a dependency is coming from and
how it's defined.



Why choose Antidote ?
=====================


- **Everything is explicit**: Some libraries using an :code:`@inject`-like decorator, such as injector_, lagom_ or python_inject_ will
  instantiate any missing arguments. Antidote won't, you have to specify explicitly what must injected.
- **Flexibility**: With the exception of dependency_injector_, most libraries will only support services (class), simple factories and singletons.
  Antidote also provides configuration, interfaces, stateful factories, lazy methods/functions, scopes, async injection.
- **Maintainability**: Again with the exception of dependency_injector_, dependency injection libraries can make it difficult to
  understand how/where a dependency is created. Typically when declaring a factory for a service (class), you won't have any way
  of finding easily the function when using the service. Antidote *always* ensures that you can. After all Antidote primary
  goal is helping you create maintainable code.
- **Performance**: Antidote's :code:`@inject` is heavily tuned for performance in the compiled version (Cython). This allows
  you to use :code:`@inject` virtually anywhere without any impact, even in tests. No other libraries goes as far as Antidote.
- **Testing**: Antidote provides testing utilities to fully isolate your tests and are tuned to ensure to be fast even
  in big projects.

.. image:: https://github.com/Finistere/antidote/raw/master/docs/_static/img/comparison_benchmark.png
    :alt: Comparison benchmark image

How does it compare to dependency_injector_ ?

The fundamental difference with dependency_injector_ is how the container of dependencies is managed. dependency_injector_
requires a container with all its dependencies to be explicitly created. Afterwards you have to manage the container yourself.

.. code-block:: python

    # my_service.py
    # Dependency Injector
    class MyService:
        pass

.. code-block:: python

    # services.py
    # Dependency Injector
    import sys
    from dependency_injector import containers, providers

    class Container(containers.DeclarativeContainer):
        my_service = providers.Singleton(MyService)

.. code-block:: python

    # app.py
    # Dependency Injector
    from dependency_injector.wiring import inject, Provide
    from services import Container
    from my_service import MyService

    @inject
    def main(my_service: MyService = Provide[Container.my_service]):
        pass


    if __name__ == '__main__':
        container = Container()
        container.wire(modules=[sys.modules[__name__]])
        main()

Compared to most libraries, with dependency_injector_ you'll always know from where a dependency is coming from. But
managing the container yourself has some flaws:

- A global object container that you have to manage in your application
- The wiring is tied to a specific container instance.

The latter can complicate your tests. dependency_injector_ recommends using the override mechanism:

.. code-block:: python

    with container.my_service.override(mock.Mock()):
        f()  # <-- overridden dependency is injected automatically

While this works well, it doesn't fully isolate your tests from each other. All the other
services are shared. Full isolation is only do-able by creating a new container re-wiring
the whole application. In pytest you would do:

.. code-block:: python

    # test.py
    import pytest

    @pytest.fixture(auto_use=True)
    def isolated_container():
        container = Container()
        container.wire(modules=[sys.modules["app"]])
        try:
            yield
        finally:
            container.unwire()

      def test_main():
        pass

Unfortunately, :code:`wire` is extremely slow because it has to check all objects and retrieve
their arguments. Doing this took *minutes* in a project I worked on. On a very simple case, Antidote provides
full isolation two orders of magnitude faster.

Let's see how the same example looks with Antidote:

.. testcode:: why_antidote

    # my_service.py
    # Antidote
    from antidote import Service

    class MyService(Service):
        pass

.. testcode:: why_antidote

    # app.py
    # Antidote
    from antidote import Provide, inject
    # from my_service import MyService

    @inject
    def main(my_service: Provide[MyService]):
        pass


    if __name__ == '__main__':
        main()

.. code-block:: python

    # test.py
    import pytest
    from antidote import world

    @pytest.fixture(auto_use=True)
    def isolated_container():
        with world.clone():  # creates a new container with the same dependencies
            yield

    def test_main():
        pass

We don't need to manage a container anymore making the code simpler. Hence Antidote is:
- simpler
- faster, see `benchmark <https://github.com/Finistere/antidote/blob/master/comparison.ipynb>`_
- as maintainable

.. _dependency_injector: https://python-dependency-injector.ets-labs.org/introduction/di_in_python.html
.. _pinject: https://github.com/google/pinject
.. _injector: https://github.com/alecthomas/injector
.. _python_inject: https://github.com/ivankorobkov/python-inject
.. _lagom: https://github.com/meadsteve/lagom
