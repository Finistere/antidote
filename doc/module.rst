Module
======

:py:mod:`dependency_manager` is mainly composed of 3 services:

- :py:class:`.DependencyContainer`: The container stores the services and
  instantiate them when necessary.
- :py:class:`.DependencyInjector`: The injector injects the dependencies of a
  function.
- :py:class:`.DependencyManager`: The manager is composed of a container and an
  injector. It exposes utility decorators and functions.

Container
---------

.. automodule:: dependency_manager.container
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__

Injector
--------

.. automodule:: dependency_manager.injector
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__

Manager
-------

.. automodule:: dependency_manager.manager
    :members:
    :member-order: bysource
    :special-members:
    :exclude-members: __dict__,__weakref__

Exceptions
----------

.. automodule:: dependency_manager.exceptions
    :members: