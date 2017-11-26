API Reference
=============

:py:mod:`antidote` is mainly composed of 3 services:

- :py:class:`.DependencyContainer`: The container stores the services and
  instantiate them when necessary.
- :py:class:`.DependencyInjector`: The injector injects the dependencies of a
  function.
- :py:class:`.DependencyManager`: The manager is composed of a container and an
  injector. It exposes utility decorators and functions.

Container
---------

.. autoclass:: antidote.container.DependencyContainer
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__


Injector
--------

.. autoclass:: antidote.injector.DependencyInjector
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__

Manager
-------

.. autoclass:: antidote.manager.DependencyManager
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__

Exceptions
----------

.. automodule:: antidote.exceptions
    :members:
    :member-order: bysource
