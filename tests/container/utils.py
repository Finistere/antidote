from antidote import DependencyNotProvidableError, Instance, Provider


class DummyProvider(Provider):
    singleton = True

    def __init__(self, data=None):
        self.data = data or dict()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
        try:
            return Instance(self.data[dependency_id],
                            singleton=self.singleton)
        except KeyError:
            raise DependencyNotProvidableError(dependency_id)


class DummyFactoryProvider(Provider):
    create_singleton = True

    def __init__(self, data=None):
        self.data = data or dict()

    def __setitem__(self, key, value):
        self.data[key] = value

    def __antidote_provide__(self, dependency_id, *args, **kwargs):
        try:
            return Instance(self.data[dependency_id](),
                            singleton=self.create_singleton)
        except KeyError:
            raise DependencyNotProvidableError(dependency_id)


class Service:
    def __init__(self, *args):
        pass


class AnotherService:
    def __init__(self, *args):
        pass


class YetAnotherService:
    def __init__(self, *args):
        pass


class ServiceWithNonMetDependency:
    def __init__(self, dependency):
        pass
