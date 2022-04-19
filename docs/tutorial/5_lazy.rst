5. Lazy
=======

We've already seen :py:func:`.injectable` which is a great way to declare classes to Antidote.
However, sometimes it's not enough as you need to manipulate an external class which you don't own
or even allow some parametrization at injection point. That's where :py:func:`.lazy` comes into play!

Decorating a function with :py:func:`.lazy` allows to lazily execute a function only when necessary:

.. testcode:: tutorial_lazy

    from antidote import lazy, inject

    # External class from a library
    class Redis:
        pass

    @lazy
    def current_redis() -> Redis:
        print("Creating Redis lazily, but only once!")
        return Redis()

.. doctest:: tutorial_lazy

    >>> @inject
    ... def run(redis: Redis = current_redis()) -> None:
    ...     pass
    >>> run()
    Creating Redis lazily, but only once!
    >>> run()
    >>> from antidote import world
    >>> world.get[Redis](current_redis())
    <Redis object ...>

Here :code:`Redis` is only created when first injected in :code:`run()`. And only once as :py:func:`.lazy`
is a singleton by default. :py:func:`.lazy` can also be used as a factory for your own classes typically
to load specific data:

.. testcode:: tutorial_lazy

    from dataclasses import dataclass
    from antidote import lazy, inject

    @dataclass
    class Session:
        id: int

    @lazy(singleton=False)
    def current_session(redis: Redis = current_redis()) -> Session:
        return Session(id=0)

.. doctest:: tutorial_lazy

    >>> s = world.get[Session](current_session())
    >>> s
    Session(id=0)
    >>> s is world.get[Session](current_session())
    False

Note that :py:func:`.lazy` will automatically use :py:func:`.inject`. You can still apply
:py:func:`.inject` yourself for finer control over the injection. Last but important use case of
:py:func:`.lazy` is parametrization!

.. testcode:: tutorial_lazy

    @dataclass
    class Template:
        path: str

    @lazy
    def load_template(path: str) -> Template:
        return Template(path=path)

    @inject
    def registration(template: Template = load_template('registration.html')):
        pass

.. doctest:: tutorial_lazy

    >>> registration()
    >>> t = world.get[Template](load_template('registration.html'))
    >>> t
    Template(path='registration.html')
    >>> t is world.get[Template](load_template('registration.html'))
    True

