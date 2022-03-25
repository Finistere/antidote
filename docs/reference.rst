*************
API Reference
*************



World
=====


world
-----

.. automodule:: antidote.world
    :members:

    .. py:data:: get
        :type: antidote.core.getter.Getter

        Used to retrieve a dependency from Antidote. A type hint can also be provided. The resulting
        dependency will be type checked if possible. Typically :py:class:`~typing.Protocol` without
        :py:func:`~typing.runtime_checkable` will not be enforced.

        .. doctest:: world_get

            >>> from antidote import world, service
            >>> @service
            ... class Dummy:
            ...     pass
            >>> world.get(Dummy)
            <Dummy ...>
            >>> # You can also provide a type hint which will be enforced if possible
            >>> world.get[object](Dummy)  # Treated by Mypy as an object
            <Dummy ...>

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


Lib
===


Service
-------

.. automodule:: antidote.service
    :members: service

.. autoclass:: antidote.service.Service
    :members: __antidote__
    :inherited-members:

    .. automethod:: parameterized

.. autoclass:: antidote.service.ABCService
    :members:


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


Interface
---------

.. automodule:: antidote.lib.interface.interface
    :members:

.. automodule:: antidote.lib.interface.qualifier
    :members:


Predicate (experimental)
------------------------

.. automodule:: antidote.lib.interface.predicate
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
    :members: Arg

    .. py:function:: inject

        Singleton instance of :py:class:`~.core.injection.Inject`

.. autoclass:: antidote.core.injection.Inject

    .. automethod:: __call__
    .. automethod:: me
    .. automethod:: get

.. autoclass:: antidote.core.getter.DependencyGetter
    :members: __call__, __getitem__

.. autoclass:: antidote.core.getter.TypedDependencyGetter
    :members: single, all, __call__


Annotations
^^^^^^^^^^^
.. automodule:: antidote.core.annotations
    :members: Get, From, FromArg

    .. autodata:: Provide

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
