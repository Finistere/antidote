# flake8: noqa
# Ignoring F811 for multiple definitions
from typing import Optional, TypeVar

from antidote._compatibility.typing import Annotated


def test_readme_simple():
    # from typing import Annotated
    # # from typing_extensions import Annotated # Python < 3.9
    from antidote import Service, inject, Provide

    class Database(Service):
        pass

    @inject
    def f(db: Provide[Database]):
        pass

    f()  # works !

    ######################

    f(Database())

    ######################

    @inject
    def f(db: Provide[Database]):
        pass

    ######################

    @inject([Database])
    def f(db):
        pass

    ######################

    @inject({'db': Database})
    def f(db):
        pass

    ######################

    # All class type hints are treated as dependencies
    @inject(auto_provide=True)
    def f(db: Database):
        pass

    ######################

    from antidote import inject, Service, Constants, const

    class Config(Constants):
        DB_HOST = const('localhost:5432')

    class Database(Service):
        @inject([Config.DB_HOST])  # self is ignored when specifying a list
        def __init__(self, host: str):
            self._host = host

    @inject({'db': Database})
    def f(db: Database):
        pass

    f()  # yeah !

    ######################

    from antidote import world

    # Retrieve dependencies by hand, in tests typically
    world.get(Config.DB_HOST)
    world.get[str](Config.DB_HOST)  # with type hint
    world.get[Database]()  # omit dependency if it's the type hint itself

    ######################

    @inject
    def f(db: Provide[Database] = None):
        # Used to tell Mypy that `db` is optional but must be either injected or given.
        assert db is not None
        pass


def test_readme():

    # from a library
    class ImdbAPI:
        def __init__(self, host: str, port: int, api_key: str):
            pass

    ######################

    # movie.py
    class MovieDB:
        """ Interface """

        def get_best_movies(self):
            pass

    ######################

    # config.py
    from antidote import Constants, const

    class Config(Constants):
        # with str/int/float, the type hint is enforced. Can be removed or extend to
        # support Enums.
        IMDB_HOST = const[str]('imdb.host')
        IMDB_PORT = const[int]('imdb.port')
        IMDB_API_KEY = const('imdb.api_key')

        def __init__(self):
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key',
                    'port': '80'
                }
            }

        def provide_const(self, name: str, arg: str):
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
        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

        def get_best_movies(self):
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
    def imdb_factory(host: Annotated[str, Get(Config.IMDB_HOST)],
                     port: Annotated[int, Get(Config.IMDB_PORT)],
                     api_key: Annotated[str, Get(Config.IMDB_API_KEY)]
                     ) -> ImdbAPI:
        return ImdbAPI(host, port, api_key)

    class IMDBMovieDB(MovieDB, Service):
        __antidote__ = Service.Conf(singleton=False)

        def __init__(self, imdb_api: Annotated[ImdbAPI, From(imdb_factory)]):
            self._imdb_api = imdb_api

        def get_best_movies(self):
            pass

    ######################

    # main.py
    # from movie import MovieDB
    # from current_movie import current_movie_db

    @inject([MovieDB @ current_movie_db])
    def main(movie_db: MovieDB = None):
        assert movie_db is not None  # for Mypy, to understand that movie_db is optional
        pass

    # Or with annotated type hints
    @inject
    def main(movie_db: Annotated[MovieDB, From(current_movie_db)]):
        pass

    main()

    ######################

    conf = Config()
    main(IMDBMovieDB(imdb_factory(
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
        main()

    ######################

    world.debug(main)
    # will output:
    """
    main
    └── Permanent implementation: MovieDB @ current_movie_db
        └──<∅> IMDBMovieDB
            └── ImdbAPI @ imdb_factory
                └── imdb_factory
                    ├── Const: Config.IMDB_API_KEY
                    │   └── Config
                    ├── Const: Config.IMDB_PORT
                    │   └── Config
                    └── Const: Config.IMDB_HOST
                        └── Config

    Singletons have no scope markers.
    <∅> = no scope (new instance each time)
    <name> = custom scope
    """