Debug dependency issues
=======================


If you encounter dependency issues or cycles, you can take a look at the whole dependency
tree with :py:func:`.world.debug`:

.. testcode:: how_to_debug

    from antidote import world, injectable, inject

    @injectable
    class MyService:
        pass

    @inject
    def f(s: MyService = inject.me()):
        pass

    print(world.debug(f))

It will output:

.. testoutput:: how_to_debug
    :options: +NORMALIZE_WHITESPACE

    f
    └── MyService

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope


.. note::

    If you're not using scopes, you only need to remember that :code:`<∅>` is equivalent
    to :code:`singleton=False`.


Now wit the more complex example presented in the home page of Antidote we have:

.. code-block:: text

    f
    └── Permanent implementation: MovieDB @ current_movie_db
        └──<∅> IMDBMovieDB
            └── ImdbAPI @ imdb_factory
                └── imdb_factory
                    ├── Const: Conf.IMDB_API_KEY
                    │   └── Conf
                    │       └── Singleton: 'conf_path' -> '/etc/app.conf'
                    ├── Const: Conf.IMDB_PORT
                    │   └── Conf
                    │       └── Singleton: 'conf_path' -> '/etc/app.conf'
                    └── Const: Conf.IMDB_HOST
                        └── Conf
                            └── Singleton: 'conf_path' -> '/etc/app.conf'

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope


If you ever encounter a cyclic dependency, it will be present with a:

.. code-block:: text

    /!\\ Cyclic dependency: X

Ambiguous dependencies, which cannot be identified uniquely through their name, such as tags,
will have their id added to help differentiate them:

.. testcode:: how_to_debug

    from antidote import LazyCall

    def current_status():
        pass

    STATUS = LazyCall(current_status)

    print(world.debug(STATUS))

will output the following

.. testoutput:: how_to_debug
    :options: +NORMALIZE_WHITESPACE

    Lazy: current_status()  #...

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope

.. code-block:: text

    Lazy: current_status()  #0P2QAw

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope
