API Reference
=============

:py:mod:`antidote` is mainly composed of 4 components:

- :py:class:`.DependencyContainer`: The container manages the dependencies,
  it stores them if necessary and uses providers to instantiate them. It also
  ensures the thread safety and does the cycle detection.
- :py:class:`.DependencyInjector`: The injector injects the dependencies of a
  function.
- :py:class:`.DependencyManager`: The manager is composed of a container, an
  injector and the  :py:class:`~.providers.DependencyFactories` provider.
  It exposes utility decorators and functions.

Manager
-------

.. autoclass:: antidote.manager.DependencyManager
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__


Injector
--------

.. autoclass:: antidote.injection.DependencyInjector
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__


Container
---------

.. autoclass:: antidote.container.DependencyContainer
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__


Providers
---------

.. autoclass:: antidote.providers.factories.DependencyFactories
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__


Exceptions
----------

.. automodule:: antidote.exceptions
    :members:
    :member-order: bysource
