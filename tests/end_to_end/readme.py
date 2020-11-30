from typing import Dict


def test_readme_simple() -> None:
    from antidote import inject, Service

    # Declare NyService as a dependency that can be injected
    class MyService(Service):
        pass

        # uses the type hint

    @inject
    def f(service: MyService):
        pass

    f()  # Service will be automatically injected if not provided
    f(MyService())  # but you can still use the function normally

    # There are also different ways to declare which dependency should be used for each
    # arguments, for example: a mapping from arguments to their dependencies
    @inject(dependencies=dict(service=MyService))
    def g(service):
        pass


def test_readme() -> None:
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

    class Conf(Constants):
        # Configuration values is identified by those class attributes. It helps
        # refactoring as it's easy to find their usage or find their definition.
        # The Constants super class will treat their associated value as the input
        # argument of get(). This allows you to load lazily any configuration.
        IMDB_HOST = 'imdb.host'
        # When used as a dependency, one will have `self.get('imdb.api_key')` injected
        IMDB_API_KEY = 'imdb.api_key'

        def __init__(self):
            """ Load configuration from somewhere """
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
        # Antidote specific configuration. By default __init__() is always auto wired,
        # meaning injected. As ImdbAPI is not itself a Service, but is provided by
        # imdb_factory, Antidote requires it to be explicitly stated. This ensures that
        # can always track back where dependencies are coming from.
        __antidote__ = Implementation.Conf().with_wiring(
            dependencies=dict(imdb_api=ImdbAPI @ imdb_factory))

        def __init__(self, imdb_api: ImdbAPI):
            self._imdb_api = imdb_api

        def get_best_movies(self):
            pass

    # Inject dependencies in f(), by default only type annotations are used. But
    # arguments name, explicit mapping, etc.. can also be used.
    @inject
    def f(movie_db: MovieDB):
        pass

    # Can be called without arguments now.
    f()

    # You can still explicitly pass the arguments to override
    # injection.
    conf = Conf()
    f(IMDBMovieDB(imdb_factory(
        # The class attributes will retrieve the actual value when called on a instance.
        # Hence this is equivalent to conf.get('imdb.host'), making your tests easier.
        host=conf.IMDB_HOST,
        api_key=conf.IMDB_API_KEY,  # <=> conf.get('imdb.api_key')
    )))

    # Or override dependencies locally within a context manager:
    with world.test.clone(overridable=True):
        world.singletons.add({
            Conf.IMDB_HOST: 'other host'
        })
        f()

    world.debug(f)
