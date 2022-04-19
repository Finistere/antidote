World
=====


.. automodule:: antidote.world
    :members:

    .. py:data:: get
        :type: antidote.core.getter.Getter

        Used to retrieve a dependency from Antidote. A type hint can also be provided. The resulting
        dependency will be type checked if possible. Typically :py:class:`~typing.Protocol` without
        :py:func:`~typing.runtime_checkable` will not be enforced.

        .. doctest:: world_get

            >>> from antidote import world, injectable
            >>> @injectable
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
