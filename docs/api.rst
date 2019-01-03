API Reference
=============


Injection
---------

.. automodule:: antidote.injection.inject
    :members:

.. automodule:: antidote.injection.wiring
    :members:


Helpers
-------

.. automodule:: antidote.helpers.registration
    :members:

.. automodule:: antidote.helpers.attrs
    :members:

.. automodule:: antidote.helpers.container
    :members:


Container
---------

.. autoclass:: antidote.container.container.DependencyContainer
    :members:
    :special-members:
    :exclude-members: __dict__,__weakref__,__init__,__repr__,__str__

.. autoclass:: antidote.container.container.Dependency
    :members:

.. autoclass:: antidote.container.container.Instance
    :members:

.. autoclass:: antidote.container.container.Provider
    :members:


Providers
---------

Factory
^^^^^^^

.. automodule:: antidote.providers.factory
    :members: FactoryProvider,Build

Resource
^^^^^^^^

.. automodule:: antidote.providers.resource
    :members: ResourceProvider

Tag
^^^

.. automodule:: antidote.providers.tag.dependency
    :members:

.. automodule:: antidote.providers.tag.provider
    :members:


Exceptions
----------

.. automodule:: antidote.exceptions
    :members:
