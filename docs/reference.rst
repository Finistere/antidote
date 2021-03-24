*************
API Reference
*************



World Utilities
===============


world
-----

.. automodule:: antidote.world
    :members:

    .. autodata:: get

    .. autodata:: lazy

.. automodule:: antidote.utils
    :members: is_compiled


world.scopes
------------

.. automodule:: antidote.world.scopes
    :members:


world.test
----------

.. automodule:: antidote.world.test
    :members:


world.test.override
-------------------

.. automodule:: antidote.world.test.override
    :members:


Dependencies
============


Service
-------

.. automodule:: antidote.service
    :members: service

.. autoclass:: antidote.service.Service
    :members: __antidote__
    :inherited-members:

    .. automethod:: parameterized


Factory
-------

.. automodule:: antidote.factory
    :members: factory

.. autoclass:: antidote.factory.Factory
    :members:
    :inherited-members:

    .. automethod:: parameterized


Constants
---------

.. autoclass:: antidote.constants.Constants
    :members:


Lazy
----

.. automodule:: antidote.lazy
    :members:


Implementation
--------------

.. automodule:: antidote.implementation
    :members:



Core
====


Injection
---------

Inject
^^^^^^
.. automodule:: antidote.core.injection
    :members: inject, Arg

Annotations
^^^^^^^^^^^
.. automodule:: antidote.core.annotations
    :members:

Wiring
^^^^^^
.. automodule:: antidote.core.wiring
    :members: Wiring, wire, WithWiringMixin


Provider
--------

.. automodule:: antidote.core.provider
    :members:

.. automodule:: antidote.core.container
    :members:

.. autoclass::antidote.core.utils.DependencyDebug
    :members:



Exceptions
==========

.. automodule:: antidote.exceptions
    :members:
