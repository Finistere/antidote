Lib
===


Injectable
----------

.. automodule:: antidote.lib.injectable
    :members:


Interface
---------

.. automodule:: antidote.lib.interface.interface
    :members:

.. automodule:: antidote.lib.interface.qualifier
    :members:


Predicate (experimental)
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: antidote.lib.interface.predicate
    :members:

Lazy
----

.. automodule:: antidote.lib.lazy.lazy
    :members: lazy

.. autoclass:: antidote.lib.lazy.lazy.LazyWrappedFunction
    :members: __call__, call, __wrapped__


Constant
--------


.. automodule:: antidote.lib.lazy

    .. py:data:: const

        Singleton instance of :py:class:`.Const`

.. automodule:: antidote.lib.lazy.constant
    :members:
    :special-members: __call__, __getitem__
