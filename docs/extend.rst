***************
Extend Antidote
***************


Inner working
=============

Antidote consists roughly of a core mechanism handling the injection and providers which
actually provide the dependencies. The injection goes trough the :py:class:`~.core.Container`,
roughly :py:mod:`.world`, to request dependencies. The latter regroups all registered providers.
It short it looks like the following ::

                            +-------------+
             tag=...  +-----> TagProvider +----+
                            +-------------+    |
                                               |
                         +------------------+  |    +--------------------+
     @implementation  +--> IndirectProvider +--+----> Container (~world) +---> @inject
                         +------------------+  |    +--------------------+
                                               |
                          +-----------------+  |
             Service  +---> ServiceProvider +--+
                          +-----------------+


The :py:class:`~.core.Container` never handles the instantiation of the dependencies itself, it
relies on providers. But it does handle thread-safety, cycle detection and singletons. When
a new dependency is requested it will try all provider to see if one of them can provide it.
If not a :py:exc:`~.exceptions.DependencyNotFoundError` is raised. If yes, the container
will cache it if it's a singleton.


Adding a Provider
=================

For simplicity, we will add a very simple provider, one that generates a random number when
:code:`'random'` is requested. The most important methods are :py:meth:`~.core.Provider.exists`
and :py:meth:`~.core.Provider.provide`. Both a are called by the :py:class:`~.core.Container`.
:py:meth:`~.core.Provider.exists` is used to check whether a dependency is supported or not
and if yes :py:meth:`~.core.Provider.provide` will be called to retrieve the dependency value.
It is expected to return a :py:class:`~.core.DependencyInstance` which specifies whether the
returned instance is a singleton or not. If yes, the :py:class:`~.core.Container` will cache
the result and the provider will never be called again.

.. testcode:: extend_antidote_add_provider

    import random
    from typing import Optional

    from antidote import world
    from antidote.core import StatelessProvider, DependencyValue, Container

    @world.provider
    class RandomProvider(StatelessProvider[str]):
        def exists(self, dependency: object) -> bool:
            return dependency == 'random'

        def provide(self, dependency: str, container: Container) -> DependencyValue:
            return DependencyValue(random.random(), scope=None)

.. doctest:: extend_antidote_add_provider

    >>> from antidote import world
    >>> world.get[float]('random')
    0...
    >>> world.get('random') == world.get('random')
    False

Note that we're inheriting from :py:class:`~.core.StatelessProvider` as we don't handle
any state. If you do handle state, you'll need a bit more work. For example, let's say we
want to add different kinds of random values such as age or names. But we do not have
them out of the box, we expect someone else to provide the examples:

.. testcode:: extend_antidote_add_provider

    import random
    from typing import Optional, Dict, List

    from antidote import world, inject, Provide
    from antidote.core import Provider, DependencyValue, Container

    @world.provider
    class RandomProvider(Provider[str]):
        # The provider must be instantiable without any arguments.
        def __init__(self, kind_to_values: Dict[str, List[object]] = None):
            super().__init__()
            self._kind_to_values: Dict[str, List[object]] = kind_to_values or dict()

        def clone(self, keep_singletons_cache: bool) -> 'RandomProvider':
            # A clone should be independent, so we copy values as new registrations should
            # not impact the clone. We don't need a deep copy as we never change the values
            # themselves.
            return RandomProvider(self._values.copy())

        def exists(self, dependency: object) -> bool:
            return dependency in self._kind_to_values

        def provide(self, dependency: str, container: Container) -> DependencyValue:
            return DependencyValue(random.choice(self._kind_to_values[dependency]),
                                   scope=None)

        def add_random(self, kind: str, values: List[object]) -> None:
            dependency = f"random:{kind}"
            # Ensures that no other provider conflicts with the dependency.
            # It roughly checks exists() on all of them.
            self._assert_cannot_provide(dependency)
            self._kind_to_values[dependency] = values

    # The recommend way is not to expose the provider directly, but to expose utility
    # functions which have the provider injected. Making them easier to use and maintain.
    # Often those would be decorators, like... @injectable !
    @inject
    def add_random(kind: str,
                   values: List[object],
                   provider: Provide[RandomProvider] = None):
        assert provider is not None
        provider.add_random(kind, values)

.. doctest:: extend_antidote_add_provider

    >>> names = ['John', 'Karl', 'Anna', 'Sophie']
    >>> add_random('name', names)
    >>> world.get[str]('random:name') in names
    True

Note that we still dont' handle anywhere thread-safety ! The methods :py:meth:`~.core.Provider.exists`
, :py:meth:`~.core.Provider.provide`, and :py:meth:`~.core.Provider.clone` are always called
in a thread-safe environment. This also means that you're not expected to call them yourself.
:py:meth:`.world.freeze` is automatically taken into account:

.. doctest:: extend_antidote_add_provider

    >>> world.freeze()
    >>> add_random('random:city', ['Paris', 'Berlin'])
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
    FrozenWorldError

If your method does not add any dependencies and is only used for instantiation, you can tell
Antidote to avoid it by decorating it with :py:func:`~.core.does_not_freeze`.



Test extensions
===============


You can test a *new kind of dependency* with :py:func:`.world.test.new`. It creates a
new world with the same providers and scopes but without any of the existing dependencies.
For a new :py:class:`.Provider` you should usually use :py:func:`.world.test.empty`. It
creates an almost empty world. To test the :code:`provide()` you should rely on
:py:func:`.world.test.maybe_provide_from`

Both world provide a simple way to define a singleton with :py:func:`.world.test.singleton` and a
factory with :py:func:`.world.test.factory`. They will behave like any other dependency,
contrary to the overrides available in :py:func:`.world.test.clone`.
