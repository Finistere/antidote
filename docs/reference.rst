API Reference
=============


World
-----

.. automodule:: antidote.world
    :members: freeze, provider, get, lazy

.. automodule:: antidote.world.singletons
    :members: set, update


Dependencies
------------

Service
^^^^^^^
.. automodule:: antidote.helpers.service
    :members: service

.. autoclass:: antidote.helpers.service.Service
    :members: __antidote__
    :inherited-members:

    .. automethod:: with_kwargs

Factory
^^^^^^^
.. automodule:: antidote.helpers.factory
    :members: factory

.. autoclass:: antidote.helpers.factory.Factory
    :members:
    :inherited-members:

    .. automethod:: with_kwargs

Constants
^^^^^^^^^
.. autoclass:: antidote.helpers.constants.Constants
    :members:

Lazy
^^^^
.. automodule:: antidote.helpers.lazy
    :members:

Implementation
^^^^^^^^^^^^^^
.. automodule:: antidote.helpers.implements
    :members:

Tags
^^^^
.. automodule:: antidote.providers.tag
    :members: Tag, Tagged


Core
----

Injection
^^^^^^^^^
.. automodule:: antidote.core.injection
    :members: inject, Arg

.. automodule:: antidote.core.wiring
    :members: Wiring, wire, WithWiringMixin

.. automodule:: antidote.core.utils
    :members:

Provider
^^^^^^^^
.. automodule:: antidote.core.provider
    :members:

.. automodule:: antidote.core.container
    :members:


Exceptions
----------

.. automodule:: antidote.exceptions
    :members:
