Core
====


Injection
---------

Inject
^^^^^^

.. automodule:: antidote.core.injection
    :members: Arg

    .. py:function:: inject

        Singleton instance of :py:class:`~.core.injection.Injector`

.. autoclass:: antidote.core.injection.Injector

    .. automethod:: __call__
    .. automethod:: me
    .. py:attribute:: get
        :type: antidote.core.getter.DependencyGetter

        :py:class:`.DependencyGetter` to explicit state the dependencies to be retrieved.
        It follows the same API as :py:obj:`.world.get`.


.. autoclass:: antidote.core.getter.DependencyGetter
    :members: __call__, __getitem__

.. autoclass:: antidote.core.getter.TypedDependencyGetter
    :members: single, all, __call__


Annotations
^^^^^^^^^^^
.. automodule:: antidote.core.annotations
    :members: Get, From, FromArg

    .. py:data:: Provide

        .. deprecated:: 1.1
            Prefer using :py:obj:`.Inject`

    .. autodata:: Inject

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
