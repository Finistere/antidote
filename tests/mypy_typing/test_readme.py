# flake8: noqa
# Ignoring F811 for multiple definitions
from typing import Optional

from typing_extensions import Annotated


def test_readme_simple() -> None:
    from antidote import inject, service

    @service
    class Database:
        pass

    @inject
    def f(db: Database = inject.me()) -> Database:
        return db

    assert isinstance(f(), Database)  # works !

    ######################

    f(Database())

    ######################

    from antidote import Inject

    @inject
    def f2(db: Inject[Database]) -> None:
        pass

    ######################

    @inject([Database])
    def f3(db: object) -> None:
        pass

    ######################

    @inject({'db': Database})
    def f4(db: object) -> None:
        pass

    ######################

    from typing import Optional

    class Dummy:
        pass

    # When the type_hint is optional and a marker like `inject.me()` is used, None will be
    # provided if the dependency does not exists.
    @inject
    def f5(dummy: Optional[Dummy] = inject.me()) -> Optional[Dummy]:
        return dummy

    assert f5() is None

    ######################

    from antidote import world

    # Retrieve dependencies by hand, in tests typically
    world.get(Database)
    world.get[Database](Database)  # with type hint
    world.get[Database]()  # omit dependency if it's the type hint itself

    ######################

    from antidote import service, inject

    @service(singleton=False)
    class QueryBuilder:
        # methods are also injected by default
        def __init__(self, db: Database = inject.me()) -> None:
            self._db = db

    @inject
    def load_data(builder: QueryBuilder = inject.me()) -> None:
        pass

    load_data()  # yeah !

    ######################

    from antidote import inject, Constants, const

    class Config(Constants):
        DB_HOST = const[str]('localhost')

    @inject
    def ping_db(db_host: str = Config.DB_HOST) -> None:
        pass

    ping_db()  # nice !

    ######################

    from antidote import inject, Constants, const

    class Config2(Constants):
        DB_HOST = const[str]()  # used as a type annotation
        DB_PORT = const[int]()  # and also to cast the value retrieved from `provide_const`
        # defaults are supported, used on LookupError
        DB_USER = const[str](default='postgres')

        def provide_const(self, *, name: str, arg: Optional[object]) -> object:
            return os.environ[name]

    import os
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '5432'

    @inject
    def check_connection(db_host: str = Config2.DB_HOST,
                         db_port: int = Config2.DB_PORT) -> None:
        pass

    check_connection()  # perfect !

    ######################

    from antidote import factory, inject

    class User:
        pass

    @factory(singleton=False)  # annotated type hints can be used or you can @inject manually
    def current_user(db: Database = inject.me()) -> User:  # return type annotation is used
        return User()

    # Note that here you *know* exactly where it's coming from.
    @inject
    def is_admin(user: User = inject.me(source=current_user)) -> None:
        pass

    ######################

    from antidote import world

    world.get(User, source=current_user)

    ######################

    from antidote import factory, inject, world

    REQUEST_SCOPE = world.scopes.new(name='request')

    @factory(scope=REQUEST_SCOPE)
    def current_user2(db: Database = inject.me()) -> User:
        return User()

    # Reset all dependencies in the specified scope.
    world.scopes.reset(REQUEST_SCOPE)


def test_interface_impl() -> None:
    from antidote import implementation, service, factory, Get

    class Cache:
        pass

    @service
    class MemoryCache(Cache):
        pass

    class Redis:
        """ class from an external library """

    @factory
    def redis_cache() -> Redis:
        return Redis()

    @implementation(Cache)
    def cache_impl() -> object:
        import os

        if os.environ.get('USE_REDIS_CACHE'):
            return Get(Redis, source=redis_cache)

        # Returning the dependency that must be retrieved
        return MemoryCache

    ######################

    from antidote import world, inject

    @inject
    def heavy_compute(cache: Cache = inject.me(source=cache_impl)) -> None:
        pass

    world.get(Cache, source=cache_impl)


def test_debugging() -> None:
    from antidote import service, inject

    @service
    class Database:
        pass

    @inject
    def f(db: Database = inject.me()) -> None:
        pass

    f()
    f(Database())  # test with specific arguments in unit tests

    ######################

    from antidote import world

    # Clone current world to isolate it from the rest
    with world.test.clone():
        x = object()
        # Override the Database
        world.test.override.singleton(Database, x)
        f()  # will have `x` injected for the Database

        @world.test.override.factory(Database)
        def override_database() -> object:
            class DatabaseMock:
                pass

            return DatabaseMock()

        f()  # will have `DatabaseMock()` injected for the Database


def test_readme() -> None:
    # from a library
    class ImdbAPI:
        def __init__(self, host: str, port: int, api_key: str):
            pass

    ######################

    # movie.py
    class MovieDB:
        """ Interface """

        def get_best_movies(self) -> None:
            pass

    ######################

    # config.py
    from antidote import Constants, const

    class Config(Constants):
        # with str/int/float, the type hint is enforced. Can be removed or extend to
        # support Enums.
        IMDB_HOST = const[str]('imdb.host')
        IMDB_PORT = const[int]('imdb.port')
        IMDB_API_KEY = const[str]('imdb.api_key')

        def __init__(self) -> None:
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key',
                    'port': '80'
                }
            }

        def provide_const(self, *, name: str, arg: Optional[str]) -> object:
            assert arg is not None
            root, key = arg.split('.')
            return self._raw_conf[root][key]

    ######################

    # current_movie.py
    # Code implementing/managing MovieDB
    from antidote import factory, inject, Service, implementation
    # from config import Config

    # Provides ImdbAPI, as defined by the return type annotation.
    @factory
    @inject([Config.IMDB_HOST, Config.IMDB_PORT, Config.IMDB_API_KEY])
    def imdb_factory(host: str, port: int, api_key: str) -> ImdbAPI:
        # Here host = Config().provide_const('IMDB_HOST', 'imdb.host')
        return ImdbAPI(host=host, port=port, api_key=api_key)

    class IMDBMovieDB(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)  # New instance each time

        @inject({'imdb_api': ImdbAPI @ imdb_factory})
        def __init__(self, imdb_api: ImdbAPI) -> None:
            self._imdb_api = imdb_api

        def get_best_movies(self) -> None:
            pass

    @implementation(MovieDB)
    def current_movie_db() -> object:
        return IMDBMovieDB  # dependency to be provided for MovieDB

    ######################

    # current_movie.py
    # Code implementing/managing MovieDB
    from antidote import factory, Service, Get, From
    # from typing import Annotated
    # # from typing_extensions import Annotated # Python < 3.9
    # from config import Config

    @factory
    def imdb_factory2(host: Annotated[str, Get(Config.IMDB_HOST)],
                      port: Annotated[int, Get(Config.IMDB_PORT)],
                      api_key: Annotated[str, Get(Config.IMDB_API_KEY)]
                      ) -> ImdbAPI:
        return ImdbAPI(host, port, api_key)

    class IMDBMovieDB2(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)

        def __init__(self, imdb_api: Annotated[ImdbAPI, From(imdb_factory2)]):
            self._imdb_api = imdb_api

        def get_best_movies(self) -> None:
            pass

    ######################

    # main.py
    # from movie import MovieDB
    # from current_movie import current_movie_db

    @inject([MovieDB @ current_movie_db])
    def main(movie_db: Optional[MovieDB] = None) -> None:
        assert movie_db is not None  # for Mypy, to understand that movie_db is optional
        pass

    # Or with annotated type hints
    @inject
    def main2(movie_db: Annotated[MovieDB, From(current_movie_db)]) -> None:
        pass

    main2()

    ######################

    conf = Config()
    main2(IMDBMovieDB(imdb_factory(
        # constants can be retrieved directly on an instance
        host=conf.IMDB_HOST,
        port=conf.IMDB_PORT,
        api_key=conf.IMDB_API_KEY,
    )))

    ######################

    from antidote import world

    # Clone current world to isolate it from the rest
    with world.test.clone():
        # Override the configuration
        world.test.override.singleton(Config.IMDB_HOST, 'other host')
        main2()

    ######################

    world.debug(main2)
