Why do I need ...
=================

... Dependency Injection ?
--------------------------

Dependency injection is a technique where objects do not instantiate themselves
their dependencies, it is up to the user or another object to supply them. A
simple example is presented below: :code:`f()` and :code:`g()` are two functions
operating on a database, they both require a connection to it. :code:`g()` is
implemented with dependency injection in mind, while :code:`f()` is not.

.. code-block:: python

    class Database:
        def __init__(self, host):
            """ Initializes database """

    def f(host):
        db = Database(host)
        # do stuff

    # With dependency injection, it's up to the user/framework to
    # provide the database.
    def g(database):
        # do stuff


Using :code:`g()` provides several advantages:

- Single Responsibility Principle: The function does not have to instantiate
  anything anymore, it only does its job.
- Open/closed principle: One can change the database for any other one, as long
  as it keeps the same interface. With :code:`f()` you would need to rewrite
  the function, as the database may need to be instantiated differently.
- As you don't have to manage dependencies in you code anymore, it becomes
  usually easier to create more modular code and readable code.
- When testing, it can be easier to supply a dummy object which mimics the
  database than mocking the :code:`Database()` itself. This helps separating
  what you *need* and what you *have*.

Now you're faced with the problem of injecting and managing your dependencies.
It is, unsurprisingly, quite easy with Python for simple projects: You have
a module with your dependencies, be it singletons or factories to instantiate
them, and you inject them at the start of your applications in your scripts or
in :code:`__main__()`. While this works really well for relatively small-sized
projects with a limited number of dependencies, it doesn't scale at all.

- Instantiation is not lazy. Often you do not need all of your dependencies and
  instantiating all of them can be costly.
- With a lot of different dependencies, it can quickly become a mess to
  properly manage them in one big file or multiple ones.
- The dependencies are defined and instantiated in different places, which is
  error-prone whenever you modify them.

The wiring and managing of all your dependencies, is what antidote is for. You
define your dependency in one place, let antidote know it exists and how to
instantiate it and you're done !


... Antidote ?
--------------

While there are several dependency injection libraries, there was none which
matched my needs or at least convinced me it could, as of 26/11/17:

- Use of type hints to inject dependencies. And provide other means to specify
  dependencies as configuration parameters cannot be injected this way for
  example.
- Standard dependency injection features: services, factories, auto-wiring...
- It has be easy to integrate with existing code.

Here is quick and non extensive list of frameworks at which I looked:

- `Dependency Injector <https://github.com/ets-labs/python-dependency-injector>`_:
  Does not use type hints, which leads to a more boilerplate code.
- `Siringa <https://github.com/h2non/siringa>`_: Does not use type hints but
  custom annotations with for :code:`'!'` to specify dependencies to be
  injected.
- `PyCDI <https://github.com/ettoreleandrotognoli/python-cdi>`_: Need to use
  :code:`call()` to execute a function. This is, IMHO, not a proper design for
  dependency injection, you either need to use :code:`call()` on all your entry
  points, or know which functions needs it. This makes it harder to use on
  existing projects.
- `Injector <https://github.com/alecthomas/injector>`_: Need to retrieve a
  service with the :code:`Injector`. Same issue as the previous library.

