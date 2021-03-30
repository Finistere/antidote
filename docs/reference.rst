*************
API Reference
*************



World
=====


world
-----

.. automodule:: antidote.world
    :members:

    .. autodata:: get

    .. autodata:: lazy


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


Utilities
=========

.. automodule:: antidote.utils
    :members: is_compiled, validated_scope, validate_injection


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
    :members: Provide, Get, From, FromArg

Wiring
^^^^^^
.. automodule:: antidote.core.wiring
    :members: Wiring, wire


Provider
--------

.. automodule:: antidote.core.provider
    :members:

.. automodule:: antidote.core.container
    :members: Scope, DependencyValue, Container

.. automodule:: antidote.core.utils
    :members:



Exceptions
==========

.. automodule:: antidote.exceptions
    :members:
