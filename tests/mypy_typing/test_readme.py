# flake8: noqa
# Ignoring F811 for multiple definitions
from typing import Optional, TypeVar

from antidote._compatibility.typing import Annotated


def test_readme_simple():
    from antidote import inject, Service, Constants, const, world, Provide, Get
    # from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9

    class Conf(Constants):
        DB_HOST = const[str]('localhost:6789')
        DB_HOST_WITHOUT_TYPE_HINT = const('localhost:6789')

    class Database(Service):  # Defined as a Service, so injectable.
        def __init__(self, host: Annotated[str, Get(Conf.DB_HOST)]):
            self._host = host  # <=> Conf().get('host')

    @inject  # Nothing is injected implicitly.
    def f(db: Provide[Database] = None):
        # Defaulting to None allows for MyPy compatibility but isn't required to work.
        assert db is not None
        pass

    f()  # works !
    f(Database('localhost:6789'))  # but you can still use the function normally

    # You can also retrieve dependencies by hand
    world.get(Conf.DB_HOST)
    world.get[str](Conf.DB_HOST)  # with type hint
    # if the dependency is the type itself, you may omit it:
    world.get[Database]()

    ######################

    class Database(Service):
        @inject(dependencies={'host': Conf.DB_HOST})
        def __init__(self, host: str):
            self._host = host

    @inject([Database])
    def f(db: Database = None):
        assert db is not None
        pass

    # Or with auto_provide=True, all class type hints will be treated as dependencies.
    # you can also explicitly say which classes with `auto_provide=[Database]`.
    @inject(auto_provide=True)
    def f(db: Database = None):
        assert db is not None
        pass


def test_readme():
    """
    Simple example where a MovieDB interface is defined which can be used
    to retrieve the best movies. In our case the implementation uses IMDB
    to dot it.
    """
    from antidote import (Constants, factory, inject, world, const, Service,
                          implementation, Get, From)
    # from typing import Annotated
    # from typing_extensions import Annotated # Python < 3.9

    class MovieDB:
        """ Interface """

    class ImdbAPI:
        """ Class from an external library. """

        def __init__(self, *args, **kwargs):
            pass

    class Conf(Constants):
        IMDB_HOST = const[str]('imdb.host')
        # Constants will by default automatically enforce the cast to int,
        # float and str. Can be removed or extended to support Enums.
        IMDB_PORT = const[int]('imdb.port')
        # But specifying a type is not required at all, it's mostly to help Mypy.
        IMDB_API_KEY = const('imdb.api_key')

        def __init__(self):
            """
            Load configuration from somewhere. You can change how you configure your
            application later, it won't impact the whole application.
            """
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key',
                    'port': '80'
                }
            }

        def get_const(self, name: str, arg: str):
            from functools import reduce
            # self.get('a.b') <=> self._raw_conf['a']['b']
            return reduce(dict.get, arg.split('.'), self._raw_conf)  # type: ignore

    # Provides ImdbAPI, as defined by the return type annotation.
    @factory
    def imdb_factory(host: Annotated[str, Get(Conf.IMDB_HOST)],
                     port: Annotated[int, Get(Conf.IMDB_PORT)],
                     api_key: Annotated[str, Get(Conf.IMDB_API_KEY)]
                     ) -> ImdbAPI:
        # Here host = Conf().get('imdb.host')
        return ImdbAPI(host=host, port=port, api_key=api_key)

    @implementation(MovieDB)
    def current_movie_db():
        return IMDBMovieDB  # dependency to be provided for MovieDB

    class IMDBMovieDB(MovieDB, Service):
        # New instance each time
        __antidote__ = Service.Conf(singleton=False)

        def __init__(self, imdb_api: Annotated[ImdbAPI, From(imdb_factory)]):
            self._imdb_api = imdb_api

    @inject
    def f(movie_db: Annotated[MovieDB, From(current_movie_db)] = None):
        assert movie_db is not None  # for Mypy
        pass

    f()

    ######################

    @factory
    @inject([Conf.IMDB_HOST, Conf.IMDB_PORT, Conf.IMDB_API_KEY])
    def imdb_factory(host: str, port: int, api_key: str) -> ImdbAPI:
        return ImdbAPI(host=host, port=port, api_key=api_key)

    class IMDBMovieDB(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)

        @inject({'imdb_api': ImdbAPI @ imdb_factory})
        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

    @inject([MovieDB @ current_movie_db])
    def f(movie_db: MovieDB = None):
        assert movie_db is not None
        pass

    ######################

    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # The class attributes will retrieve the actual value when called on a instance.
        # Hence this is equivalent to conf.get('imdb.host'), making your tests easier.
        host=conf.IMDB_HOST,
        port=conf.IMDB_PORT,
        api_key=conf.IMDB_API_KEY,  # <=> conf.get('imdb.api_key')
    )))

    ######################

    # When testing you can also override locally some dependencies:
    with world.test.clone(keep_singletons=True):
        world.test.override.singleton(Conf.IMDB_HOST, 'other host')
        f()

    ######################

    world.debug(f)
    # will output:
    """
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
    """