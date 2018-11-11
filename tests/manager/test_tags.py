from antidote import DependencyManager, TagProvider, Tagged, TaggedDependencies


def test_inject_tagged():
    manager = DependencyManager()

    @manager.register
    class Service:
        pass

    tag_provider = manager.providers[TagProvider]  # type: TagProvider
    tag_provider.register(Service, tags=['test'])

    @manager.inject(arg_map=(Tagged('test'),))
    def f(test_tagged: TaggedDependencies):
        return test_tagged

    dependencies = list(f())

    assert 1 == len(dependencies)

    assert isinstance(dependencies[0], Service)
    assert manager.container[Service] is dependencies[0]


def test_register_tags():
    manager = DependencyManager()

    @manager.register(tags=['test'])
    class Service:
        pass

    tag_provider = manager.providers[TagProvider]  # type: TagProvider

    dependencies = list(tag_provider.__antidote_provide__(Tagged('test')).item)

    assert 1 == len(dependencies)

    assert isinstance(dependencies[0], Service)
    assert manager.container[Service] is dependencies[0]


def test_factory_tags():
    manager = DependencyManager()

    class Service:
        pass

    @manager.factory(tags=['test'])
    def f() -> Service:
        return Service()

    tag_provider = manager.providers[TagProvider]  # type: TagProvider

    dependencies = list(tag_provider.__antidote_provide__(Tagged('test')).item)

    assert 1 == len(dependencies)

    assert isinstance(dependencies[0], Service)
    assert manager.container[Service] is dependencies[0]
