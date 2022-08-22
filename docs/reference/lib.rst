Lib
===


Injectable
----------

.. automodule:: antidote.lib.injectable_ext
    :members:


Interface
---------

.. py:currentmodule:: antidote.lib.interface_ext

.. autofunction:: antidote_lib_interface

.. py:data:: interface
    :canonical: antidote.lib.interface_ext.interface
    :type: antidote.lib.interface_ext.Interface

    Singleton instance of :py:class:`~.Interface`

.. autoclass:: Interface
    :special-members: __call__

    .. autoproperty:: lazy
        :noindex:

.. autoclass:: InterfaceLazy
    :members:
    :special-members: __call__

.. autoclass:: implements
    :members:

.. autofunction:: is_interface

.. autoclass:: instanceOf
    :members:

.. autoclass:: FunctionInterface
    :members:
    :special-members: __wrapped__

.. autoclass:: LazyInterface
    :members:
    :special-members: __wrapped__


.. autoexception:: AmbiguousImplementationChoiceError

.. automodule:: antidote.lib.interface_ext.predicate
    :members:

.. automodule:: antidote.lib.interface_ext.qualifier
    :members:

Lazy
----

.. py:currentmodule:: antidote.lib.lazy_ext

.. autofunction:: antidote_lib_lazy

.. py:data:: lazy
    :canonical: antidote.lib.lazy_ext.lazy
    :type: antidote.lib.lazy_ext.Lazy

    Singleton instance of :py:class:`~.Lazy`

.. autoclass:: Lazy
    :members:
    :special-members: __call__

.. autofunction:: is_lazy

.. py:data:: const
    :canonical: antidote.lib.lazy_ext.const
    :type: antidote.lib.lazy_ext.Const

    Singleton instance of :py:class:`~.Const`

.. autoclass:: Const
    :members:
    :special-members: __call__

.. autoclass:: LazyFunction
    :members: __wrapped__

.. autoclass:: LazyMethod
    :members: __wrapped__

.. autoclass:: LazyProperty
    :members: __wrapped__

.. autoclass:: LazyValue
    :members: __wrapped__
