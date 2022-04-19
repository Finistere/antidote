Constant
========


From the environment
--------------------

.. testcode:: recipes_constants_environment

    from antidote import const

    class Env:
        # Rely on variable name
        SECRET = const.env()
        # Default value if the variable does not exist
        MISSING_VAR = const.env(default='missing')
        # Automatic conversion is enabled for int, float and all enums.
        PORT = const.env[int]()
        # Override variable name
        HOST = const.env('HOSTNAME')
        # Mix of previous options
        THRESHOLD = const.env[float]('MY_THRESHOLD', default=2.3)

.. doctest:: recipes_constants_environment

    >>> import os
    >>> from antidote import world, inject
    >>> os.environ['SECRET'] = 'my_secret'
    >>> world.get[str](Env.SECRET)
    'my_secret'
    >>> @inject
    ... def f(secret: str = Env.SECRET) -> str:
    ...     return secret
    >>> f()
    'my_secret'


Custom
------

Constant can be loaded with arbitrary logic. Antidote differentiate two cases: stateless and
stateful loading. In all cases the function must support the following arguments:

- :code:`name`: name of the constant.
- :code:`arg:`: optional argument given to :code:`const(arg)`.
- :code:`tpe`: optional type specified with :code:`const[tpe]()`.

Both :code:`arg` and :code:`tpe` default to :py:obj:`None` if not specified with :py:obj:`.const`.

Stateless
^^^^^^^^^
The previously shown :py:attr:`.Const.env` is actually implemented with a stateless factory like
this:

.. testcode:: recipes_constants_environment

    import os
    from enum import Enum
    from typing import Optional, Type, TypeVar

    from antidote import const

    T = TypeVar('T')


    # Convert automatically any of the type returning True with convert()
    @const.provider
    def env(name: str, arg: Optional[int]) -> str:
        return os.environ[arg or name]


    @env.converter  # optional, called whenever a type was specified.
    def env_converter(value: str, tpe: Type[T]) -> T:
        if issubclass(tpe, (int, str, float, Enum)):
            return tpe(value)
        raise TypeError(f"Unsupported {tpe}")


    class Env:
        # defaults, type hints, conversion, etc... are all the same.
        PORT = env.const[int](default=80)
        HOST = env.const[str]("HOSTNAME")

.. doctest:: recipes_constants_environment

    >>> from antidote import world, inject
    >>> world.get[int](Env.PORT)
    80
    >>> @inject
    ... def f(port: int = Env.PORT) -> str:
    ...     return port
    >>> f()
    80

Stateful
^^^^^^^^
Configuration can be stored in a lot of different formats, or even be retrieved on a
remote endpoint at start-up. Most of the time you would load it only once an re-use it afterwards:

.. testcode:: recipes_constants_dictionary

    from functools import reduce
    from typing import Optional, Tuple, Union

    from antidote import const, injectable


    @injectable
    class Conf:
        def __init__(self) -> None:
            self.__raw_conf = {
                "host": "localhost",
                "aws": {
                    "api_key": "my key"
                }
            }

        @const.provider
        def get(self,
                name: str,
                arg: Optional[Union[str, Tuple[str, ...]]]
                ) -> str:
            assert arg is not None  # could also use name if arg is None
            if isinstance(arg, str):
                arg = (arg,)  # for convenience
            # retrieves the value recursively
            return reduce(dict.get, arg, self.__raw_conf)  # type: ignore

        HOST = get.const('host')
        AWS_API_KEY = get.const(('aws', 'api_key'))
        AWS_SECRET_KEY = get.const(('aws', 'secret_key'), default='')


.. doctest:: recipes_constants_dictionary

    >>> from antidote import world, inject
    >>> world.get(Conf.HOST)
    'localhost'
    >>> world.get(Conf.AWS_API_KEY)
    'my key'
    >>> @inject
    ... def f(key: str = Conf.AWS_API_KEY) -> str:
    ...     return key
    >>> f()
    'my key'
