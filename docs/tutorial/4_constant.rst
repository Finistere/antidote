4. Constant
===========


Configuration, or more generally constants, can be found in any application. Antidote provides
a simple abstraction layer :py:obj:`.const` which allows you to re-define later *how* you
retrieve those constants without breaking your users:

.. testsetup:: tutorial_conf

    import os
    os.environ['HOST'] = 'example.com'

.. testcode:: tutorial_conf

    from antidote import inject, const

    class Config:
        PORT = const(3000)
        HOST = const('example.com')

    @inject
    def absolute_url(path: str,
                     host: str = Config.HOST,
                     port: int = Config.PORT
                     ) -> str:
        return f"https://{host}:{port}{path}"


.. doctest:: tutorial_conf

    >>> absolute_url("/user/1")
    'https://example.com:3000/user/1'
    >>> absolute_url('/dog/2', port=80)
    'https://example.com:80/dog/2'

Now :py:obj:`.const` really shines when your constants aren't hard-coded. With configuration
coming from environment variables you can use :py:attr:`~.Const.env`:

.. testcode:: tutorial_conf

    class Config:
        PORT = const.env[int](default=80)
        HOST = const.env()

    @inject
    def address(host: str = Config.HOST, port: int = Config.PORT) -> str:
        return f"{host}:{port}"

.. doctest:: tutorial_conf

    >>> address()
    'example.com:80'

There's actually a lot going on here! :py:attr:`~.Const.env` uses by default he name of the
constant to infer the environment variable. It can be overridden explicitly with:

.. testcode:: tutorial_conf

    class Config:
        PORT = const.env[int]('MY_PORT', default=80)
        HOST = const.env('MY_HOST')

A default value can also be provided as shown with :code:`PORT`. Last but not least you can enforce
a specific type. :py:attr:`~.Const.env` will automatically convert the value for :py:class:`int`,
:py:class:`str`, :py:class:`float` and all :py:class:`~enum.Enum`.

Obviously you can also have your custom logic which can be *stateless* like :py:attr:`~.Const.env`
or *stateful* when loading configuration files from disk/remote server.
For more examples see the :doc:`configuration recipes </recipes/constant>`.
