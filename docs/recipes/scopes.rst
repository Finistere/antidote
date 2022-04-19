Scopes
======

.. _recipes-scopes:

A dependency may be associated with a scope. If so it'll cached for as along as the scope is
valid. The most common scope being the singleton scope where dependencies are cached forever.
When the scope is set to :py:obj:`None`, the dependency value will be retrieved each time.
Scopes can be create through :py:func:`.world.scopes.new`. The name is only used to
have a friendly identifier when debugging.

.. doctest:: recipes_scope

    >>> from antidote import world
    >>> REQUEST_SCOPE = world.scopes.new(name='request')

To use the newly created scope, use :code:`scope` parameters:

.. doctest:: recipes_scope

    >>> from antidote import injectable
    >>> @injectable(scope=REQUEST_SCOPE)
    ... class Dummy:
    ...     pass

As :code:`Dummy` has been defined with a custom scope, the dependency value will
be kep as long as :code:`REQUEST_SCOPE` stays valid. That is to say, until you reset
it with :py:func:`.world.scopes.reset`:

.. doctest:: recipes_scope

    >>> current = world.get(Dummy)
    >>> current is world.get(Dummy)
    True
    >>> world.scopes.reset(REQUEST_SCOPE)
    >>> current is world.get(Dummy)
    False

In a Flask app for example you would then just reset the scope after each request:


.. code-block:: python

    from flask import Flask, Request
    from antidote import factory

    app = Flask(__name__)

    @app.after_request
    def reset_request_scope():
        world.scopes.reset(REQUEST_SCOPE)

    @lazy(scope=REQUEST_SCOPE)
    def current_request() -> Request:
        from flask import request
        return request

