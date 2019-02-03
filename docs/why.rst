Why do I need ...
=================

... Dependency Injection ?
--------------------------

Dependency injection is a technique where objects do not instantiate themselves
their dependencies, it is up to its user to supply them. A simple example
is presented below: :code:`f()` and :code:`g()` are two functions operating on
a database, they both require a connection to it. :code:`g()` is implemented
with dependency injection in mind, while :code:`f()` is not.

.. code-block:: python

    class Database:
        def __init__(self, host: str):
            """ Initializes database """

    def f(host: str):
        db = Database(host)
        # do stuff

    # With dependency injection, it's up to the user/framework to
    # provide the database.
    def g(database: Database):
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
really convinced me. At the minimum it should have:

- Use of type hints to inject dependencies. And provide other means to specify
  dependencies as configuration parameters cannot be injected this way for
  example.
- Flexible enough to have standard dependency injection features: services,
  factories, auto-wiring, tags, parameter injection, etc...
- It has be easy to integrate with existing code.

The closest I am aware of is `Injector <https://github.com/alecthomas/injector>`_.
But I don't really like the design of :code:`Injector`. It may be just a matter of
taste, but I think a dependency injection framework should be the most declarative
possible. Antidote only works with decorators out of the box, it does not require
of you to be aware of a global instance managing your dependencies. You only
declare what should and can be injected. Behind the scene all the wiring is done
automatically.
