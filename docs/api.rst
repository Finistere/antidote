API Reference
=============

:py:mod:`antidote` is mainly composed of 4 components:

- :py:class:`.DependencyContainer`: The container manages the dependencies,
  it stores them if necessary and uses providers to instantiate them. It also
  ensures the thread safety and does the cycle detection.
- :py:class:`.DependencyInjector`: The injector injects the dependencies of a
  function.
- :py:class:`.DependencyManager`: The manager is composed of a container, an
  injector and the  :py:class:`~.providers.FactoryProvider` provider.
  It exposes utility decorators and functions.

Manager
-------

.. autoclass:: antidote.manager.DependencyManager
    :members:


Injector
--------

.. autoclass:: antidote.injector.DependencyInjector
    :members:


Container
---------

.. autoclass:: antidote.container.DependencyContainer
    :members:
    :special-members:
    :exclude-members: __dict__,__weakref__,__init__,__repr__

.. autoclass:: antidote.container.Prepare
    :members:


Providers
---------

.. autoclass:: antidote.providers.factories.FactoryProvider
    :members:
    :special-members:
    :exclude-members: __dict__,__weakref__,__init__,__repr__


.. autoclass:: antidote.providers.parameters.ParameterProvider
    :members:
    :special-members:
    :exclude-members: __dict__,__weakref__,__init__,__repr__


Exceptions
----------

.. automodule:: antidote.exceptions
    :members:
