def test_readme_simple():
    from antidote import inject, Service, Constants

    class Conf(Constants):
        # Configuration values are identified by public uppercase class
        # attributes. It helps refactoring as it's easy to find their usage
        # and their definition.
        # The Constants super class will treat their associated value as the input
        # argument of get(). This allows you to load lazily any configuration.
        DB_HOST = 'host'

        def __init__(self):
            self._data = {'host': 'localhost:6789'}

        def get(self, key):
            return self._data[key]

    # Declare Database as a dependency that can be injected
    class Database(Service):
        # Antidotes configuration for this class. `__init__()` is wired (injected) by
        # default.
        __antidote__ = Service.Conf().with_wiring(
            # Specifying that arguments named 'host' should be injected with the
            # dependency Conf.DB_HOST.
            dependencies=dict(host=Conf.DB_HOST))

        # You could have wired yourself `__init__()` by applying:
        # @inject(dependencies=dict(host=Conf.DB_HOST))
        def __init__(self, host: str):
            self._host = host

    # Inject dependencies in f(), by default only type annotations are used. But
    # arguments name, explicit mapping, etc.. can also be used.
    @inject
    def f(db: Database = None):
        # Defaulting to None allows for MyPy compatibility but isn't required to work.
        assert db is not None
        pass

    f()  # Service will be automatically injected if not provided
    f(Database('localhost:6789'))  # but you can still use the function normally


def test_readme():
    """
    Simple example where a MovieDB interface is defined which can be used
    to retrieve the best movies. In our case the implementation uses IMDB
    to dot it.
    """
    from antidote import Constants, factory, Implementation, inject, world

    class MovieDB:
        """ Interface """

        def get_best_movies(self):
            pass

    class ImdbAPI:
        """ Class from an external library. """

        def __init__(self, *args, **kwargs):
            pass

    # Defining a singleton. Can only be overridden in tests.
    world.singletons.add('conf_path', '/...')

    class Conf(Constants):
        IMDB_HOST = 'imdb.host'
        IMDB_API_KEY = 'imdb.api_key'

        # `use_names=True` specifies that Antidote can use the argument names
        # when type hints are not present or too generic (builtins typically).
        __antidote__ = Constants.Conf().with_wiring(use_names=True)

        def __init__(self, conf_path: str):
            """ Load configuration from `conf_path` """
            self._raw_conf = {
                'imdb': {
                    'host': 'dummy_host',
                    'api_key': 'dummy_api_key'
                }
            }

        def get(self, key):
            """
            self.get('a.b') <=> self._raw_conf['a']['b']
            """
            from functools import reduce
            return reduce(dict.get, key.split('.'), self._raw_conf)  # type: ignore

    # ImdbAPI will be provided by this factory, as defined by the return type annotation.
    # The dependencies arguments specifies what must be injected
    @factory(dependencies=(Conf.IMDB_HOST, Conf.IMDB_API_KEY))
    def imdb_factory(host: str, api_key: str) -> ImdbAPI:
        # Here host = Conf().get('imdb.host')
        return ImdbAPI(host=host, api_key=api_key)

    # Implementation tells Antidote that this class should be used as an implementation of
    # the interface MovieDB
    class IMDBMovieDB(MovieDB, Implementation):
        # As ImdbAPI is provided by imdb_factory, Antidote requires it to be explicitly
        # specified. This ensures that can always track back where dependencies are
        # coming from.
        __antidote__ = Implementation.Conf().with_wiring(
            dependencies=dict(imdb_api=ImdbAPI @ imdb_factory))

        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

        def get_best_movies(self):
            pass

    @inject
    def f(movie_db: MovieDB = None):
        assert movie_db is not None
        pass

    # You can also retrieve dependencies by hand
    world.get[str](Conf.IMDB_HOST)  # the result will be cast to `str`
    # To avoid repetition, if the type is the dependency itself you can do:
    world.get[IMDBMovieDB]()

    # If you need to handle multiple different api_keys for some reason you can
    # specify them in the dependency itself:
    world.get[ImdbAPI](ImdbAPI @ imdb_factory.with_kwargs(api_key='XX'))
    # As imdb_factory returns a singleton, by default, this will also be the case
    # here. Using the same API key, will return the same instance. This avoids boilerplate
    # code when the same instance is needed with different arguments. The same works
    # with a Service. In the previous example you could have
    # used `Database.with_kwargs(host='something')`

    # Like before you can call f() without any arguments:
    f()

    # You can still explicitly pass the arguments to override
    # injection.
    conf = Conf('/path')
    f(IMDBMovieDB(imdb_factory(
        # The class attributes will retrieve the actual value when called on a instance.
        # Hence this is equivalent to conf.get('imdb.host'), making your tests easier.
        host=conf.IMDB_HOST,
        api_key=conf.IMDB_API_KEY,  # <=> conf.get('imdb.api_key')
    )))

    # When testing you can also override locally some dependencies:
    with world.test.clone(overridable=True, keep_singletons=True):
        world.test.override.singleton({
            Conf.IMDB_HOST: 'other host'
        })
        f()

    # If you encounter issues you can ask Antidote for a summary of what's happening
    # for a specific dependency. It becomes useful as an cycle/instantiation error
    # deep within the dependency tree results in a complex error stack.
    world.debug(f)
    """
    f
    └── Static link: MovieDB -> IMDBMovieDB
        └── IMDBMovieDB
            └── ImdbAPI @ imdb_factory
                └── imdb_factory
                    ├── Const: Conf.IMDB_API_KEY
                    │   └── Lazy: Conf()  #0BjHAQ
                    │       └── Singleton 'conf_path' -> '/...'
                    └── Const: Conf.IMDB_HOST
                        └── Lazy: Conf()  #0BjHAQ
                            └── Singleton 'conf_path' -> '/...'
    """

    # For example suppose we don't have the singleton `'conf_path'`
    with world.test.clone(keep_singletons=False):
        world.debug(f)
        # will output the following. As you can see, 'conf_path` is not found. Hence
        # when Conf will be instantiated it will fail.
        """
        f
        └── Static link: MovieDB -> IMDBMovieDB
            └── IMDBMovieDB
                └── ImdbAPI @ imdb_factory
                    └── imdb_factory
                        ├── Const: Conf.IMDB_API_KEY
                        │   └── Lazy: Conf()  #0BjHAQ
                        │       └── /!\\ Unknown: 'conf_path'
                        └── Const: Conf.IMDB_HOST
                            └── Lazy: Conf()  #0BjHAQ
                                └── /!\\ Unknown: 'conf_path'
        """
