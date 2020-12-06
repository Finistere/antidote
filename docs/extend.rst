***************
Extend Antidote
***************

While Antidote provides several ways to handle your dependencies out of the box, it may
not be enough. But don't worry, Antidote got you covered ! It is designed from the ground
up to have an easily extendable core mechanism. Services, resources and tags are all
handled in the same way, through a custom :py:class:`.Provider` ::

                            +-------------+
             tag=...  +-----> TagProvider +----+
                            +-------------+    |
                                               |
                         +------------------+  |    +----------+    +-------------------+
     @implementation  +--> IndirectProvider +-------> Provider +----> Container (world) +---> @inject
                         +------------------+  |    +----------+    +-------------------+
                                               |
                          +-----------------+  |
             Service  +---> ServiceProvider +--+
                          +-----------------+


The container never handles the instantiation of the dependencies itself, it mostly
handles their scope. Let's suppose you want to inject a random number through Antidote,
without passing through a Service. You could do it the following way:


.. testcode:: how_to_provider

    import random
    from typing import Hashable, Optional

    from antidote import world
    from antidote.core import StatelessProvider, DependencyInstance, Container

    @world.provider
    class RandomProvider(StatelessProvider):
        def exists(self, dependency: Hashable) -> bool:
            return dependency == 'random'

        def provide(self, dependency: Hashable, container: Container) -> DependencyInstance:
            return DependencyInstance(random.random(), singleton=False)

.. doctest:: how_to_provider

    >>> from antidote import world
    >>> world.get('random')
    0...
    >>> world.get('random') == world.get('random')
    False

Provider are in most cases tried sequentially. So if a provider returns nothing,
it is simply ignored and another provider is tried. For the same reason it is not
recommended to have a lot of different :py:class:`.Provider`\ s as this
implies a performance penalty.