Core
====

.. py:currentmodule:: antidote.core


Injection
---------

.. py:data:: inject
    :canonical: antidote.core.inject
    :type: antidote.core.Inject

    Singleton instance of :py:class:`.Inject`

.. autoclass:: antidote.core.Inject
    :members:
    :special-members: __call__

.. autodata:: antidote.core.InjectMe

.. autoclass:: ParameterDependency
    :members:

.. autoclass:: Wiring
    :members:

.. autofunction:: wire


Catalog
-------

.. py:data:: world
    :canonical: antidote.core.world
    :type: antidote.core.PublicCatalog

    Default catalog for all dependencies

.. py:data:: app_catalog
    :canonical: antidote.core.app_catalog
    :type: antidote.core.ReadOnlyCatalog

    Current catalog used as defined by :py:obj:`.inject`

.. autofunction:: new_catalog

.. autoclass:: CatalogId
    :members:

.. autoclass:: PublicCatalog
    :members:

.. autoclass:: Catalog
    :members:

.. autoclass:: ReadOnlyCatalog
    :members:
    :inherited-members:
    :special-members: __getitem__, __contains__

.. autofunction:: is_catalog

.. autofunction:: is_readonly_catalog


Test Context
------------

.. autoclass:: TestContextBuilder
    :members:

.. autoclass:: CatalogOverrides
    :members:

.. autoclass:: CatalogOverride
    :members:
    :special-members: __setitem__, __delitem__


Scopes
------

.. autoclass:: ScopeGlobalVar
    :members:

.. autoclass:: ScopeVarToken
    :members:

.. autoclass:: Missing
    :members:


Provider
--------

.. autoclass:: Provider
    :members:

.. autoclass:: ProvidedDependency
    :members:

.. autoclass:: ProviderCatalog
    :members:

.. autoclass:: LifeTime
    :members:

.. autoclass:: Dependency
    :members:

.. autoclass:: dependencyOf
    :members:

.. autoclass:: DependencyDebug
    :members:

.. autoclass:: DebugInfoPrefix
    :members:


Exceptions
----------

.. automodule:: antidote.core.exceptions
    :members:
