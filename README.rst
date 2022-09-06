########
Antidote
########

.. image:: https://img.shields.io/pypi/v/antidote.svg
  :target: https://pypi.python.org/pypi/antidote

.. image:: https://img.shields.io/pypi/l/antidote.svg
  :target: https://pypi.python.org/pypi/antidote

.. image:: https://img.shields.io/pypi/pyversions/antidote.svg
  :target: https://pypi.python.org/pypi/antidote

.. image:: https://github.com/Finistere/antidote/actions/workflows/main.yml/badge.svg?branch=master
  :target: https://github.com/Finistere/antidote/actions/workflows/main.yml

.. image:: https://codecov.io/gh/Finistere/antidote/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/Finistere/antidote

.. image:: https://readthedocs.org/projects/antidote/badge/?version=latest
  :target: http://antidote.readthedocs.io/en/latest/?badge=latest


Antidote is a dependency injection micro-framework for Python 3.7+, featuring:

- Strong focus on typing and putting type hints to work
- Scalable from small/simple usage to very right "framework frameworks"

It is built on the idea of having a **declarative**, **explicit** and **decentralized** definition of dependencies at the type / function / variable definition.
These definitions can be easily tracked down, including by static tooling and startup-time analysis.

Features are built with a strong focus on **maintainability**, **simplicity** and **ease of use** in mind. Everything is statically typed (mypy & pyright), documented with tested examples, and can be easily used in existing code and tested in isolation.


************
Installation
************


To install Antidote, simply run this command:

.. code-block:: bash

    pip install antidote



*************
Help & Issues
*************


Feel free to open an `issue <https://github.com/Finistere/antidote/issues>`_ or a `discussion <https://github.com/Finistere/antidote/discussions>`_ on `Github <https://github.com/Finistere/antidote>`_ for questions, issues, proposals, etc. !



*************
Documentation
*************


Tutorial, reference and more can be found in the `documentation <https://antidote.readthedocs.io/en/latest>`_. Some quick links:

- `Guide <https://antidote.readthedocs.io/en/latest/guide/index.html>`_
- `Reference <https://antidote.readthedocs.io/en/latest/reference/index.html>`_
- `Changelog <https://antidote.readthedocs.io/en/latest/changelog.html>`_



********
Overview
********


Accessing dependencies
======================

Antidote works with a :code:`Catalog` which is a sort of "collection" of dependencies. Multiple collections can co-exist, but :code:`world` is used by default. The most common form of a dependency is an instance of a given class:

.. code-block:: python

    from antidote import injectable

    @injectable
    class Service:
        pass

    world[Service]  # retrieve the instance
    world.get(Service, default='something')  # similar to a dict

By default, :code:`@injectable` defines a singleton. However, alternative lifetimes (how long the :code:`world` keeps value alive in its cache) can exist, such as :code:`transient`, where nothing is cached at all.

Dependencies can also be injected into a function/method with :code:`@inject`. For both kinds of callables, Mypy, Pyright and PyCharm will infer the correct types.

.. code-block:: python

    from antidote import inject

    @inject  #                      ⯆ Infers the dependency from the type hint
    def f(service: Service = inject.me()) -> Service:
        return service

    f()  # service injected
    f(Service())  # useful for testing: no injection, argument is used

:code:`@inject` supports a variety of ways to bind arguments to their dependencies (if any.) This binding is *always* explicit:

.. code-block:: python

    from antidote import InjectMe

    # recommended with inject.me() for best static-typing experience
    @inject
    def f2(service = inject[Service]):
        ...

    @inject(kwargs={'service': Service})
    def f3(service):
        ...

    @inject
    def f4(service: InjectMe[Service]):
        ...

Classes can also be fully wired, with all methods injected, by using :code:`@wire`. It is also possible to
inject the first argument, commonly named :code:`self`, of a method with an instance of a class:

.. code-block:: python

    @injectable
    class Dummy:
        @inject.method
        def method(self) -> 'Dummy':
            return self

    # behaves like a class method
    assert Dummy.method() is world[Dummy]

    # useful for testing: when accessed trough an instance, no injection
    dummy = Dummy()
    assert dummy.method() is dummy



Defining dependencies
======================

Antidote comes out-of-the-box with 4 kinds of dependencies:

-   :code:`@injectable` classes for which an instance is provided.

    .. code-block:: python

        from antidote import injectable

        #           ⯆ optional: would just call Service() otherwise.
        @injectable(factory_method='load')
        class Service:
            @classmethod
            def load(cls) -> 'Service':
                return cls()

        world[Service]


-   :code:`const` for defining simple constants.

    .. code-block:: python

        from antidote import const

        # Used as namespace
        class Conf:
            TMP_DIR = const('/tmp')

            # From environment variables, lazily retrieved
            LOCATION = const.env("PWD")
            USER = const.env()  # uses the name of the variable
            PORT = const.env(convert=int)  # convert the environment variable to a given type
            UNKNOWN = const.env(default='unknown')

        world[Conf.TMP_DIR]

        @inject
        def f(tmp_dir: str = inject[Conf.TMP_DIR]):
            ...

-   :code:`@lazy` function calls (taking into account arguments) used for (stateful-)factories, parameterized dependencies, complex constants, etc.

    .. code-block:: python

        from dataclasses import dataclass

        from antidote import lazy

        @dataclass
        class Template:
            name: str

        # the wrapped template function is only executed when accessed through world/@inject
        @lazy
        def template(name: str) -> Template:
            return Template(name=name)

        # By default a singleton, so it always returns the same instance of Template
        world[template(name="main")]

        @inject
        def f(main_template: Template = inject[template(name="main")]):
            ...

    :code:`@lazy` will automatically apply :code:`@inject` and can also be a value, property or even a method similarly to :code:`@inject.method`.

-   :code:`@interface` for which one or multiple implementations can be provided.

    .. code-block:: python

        from antidote import interface, implements

        @interface
        class Task:
            pass

        @implements(Task)
        class CustomTask(Task):
            pass

        world[Task]  # instance of CustomTask

    The interface does not need to be a class. It can also be a :code:`Protocol`, a function or a :code:`@lazy` function call!

    .. code-block:: python

        @interface
        def callback(event: str) -> bool:
            ...

        @implements(callback)
        def on_event(event: str) -> bool:
            # do stuff
            return True

        # returns the on_event function
        assert world[callback] is on_event

    :code:`@implements` will enforce as much as possible that the interface is correctly implemented. Multiple implementations can also be retrieved. Conditions, filters on metadata and weighting implementation are all supported to allow full customization of which implementation should be retrieved in which use case.

Each of those have several knobs to adapt them to your needs which are covered in the documentation.


Testing & Debugging
===================

Injected functions can typically be tested by passing arguments explicitly but it's not always enough. Antidote provides a test context for full test isolation. The test context allows overriding any dependencies:

.. code-block:: python

    original = world[Service]
    with world.test.clone() as overrides:
        # dependency value is different, but it's still a singleton Service instance
        assert world[Service] is not original

        # override examples
        overrides[Service] = 'x'
        assert world[Service] == 'x'

        del overrides[Service]
        assert world.get(Service) is None

        @overrides.factory(Service)
        def build_service() -> object:
            return 'z'


        # Test context can be nested and it wouldn't impact the current test context
        with world.test.clone() as nested_overrides:
            ...

    # Outside the test context, nothing changed.
    assert world[Service] is original


Antidote also provides introspection capabilities with :code:`world.debug`  which returns a nicely-formatted tree to show what Antidote actually sees, without actually executing anything:

.. code-block:: text

    🟉 <lazy> f()
    └── ∅ Service
        └── Service.__init__
            └── 🟉 <const> Conf.HOST

     ∅ = transient
     ↻ = bound
     🟉 = singleton


Going Further
=============

- Scopes are supported. Defining a :code:`ScopeGlobalVar` and using it as a dependency will force any dependents to be updated whenever it changes (a request for example).
- Multiple catalogs can be used which lets you expose only a subset of your API (dependencies) to your consumer within a catalog.
- You can easily define your kind of dependencies with proper typing from both :code:`world` and :code:`inject`. :code:`@injectable`, :code:`@lazy`, :code:`inject.me()` etc.. all rely on Antidote's core (:code:`Provider`, :code:`Dependency`, etc.) which is part of the public API.

Check out the `Guide <https://antidote.readthedocs.io/en/latest/guide/index.html>`_ which goes more in depth or the `Reference <https://antidote.readthedocs.io/en/latest/reference/index.html>`_ for specific features.

*****************
How to Contribute
*****************


1. Check for open issues or open a fresh issue to start a discussion around a feature or a bug.
2. Fork the repo on GitHub. Run the tests to confirm they all pass on your  machine. If you cannot find why it fails, open an issue.
3. Start making your changes to the master branch.
4. Send a pull request.

*Be sure to merge the latest from "upstream" before making a pull request!*

If you have any issue during development or just want some feedback, don't hesitate to open a pull request and ask for help ! You're also more than welcome to open a discussion or an issue on any topic!

But, no code changes will be merged if they do not pass mypy, pyright, don't have 100% test coverage or documentation with tested examples (if relevant.)
