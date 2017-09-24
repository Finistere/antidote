from .container import ServicesContainer
import wrapt

_container = ServicesContainer()


def inject(**inject_kwargs):

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        args, kwargs = _container.builder.build(wrapped, args, kwargs,
                                                **inject_kwargs)
        return wrapped(*args, **kwargs)

    return wrapper


def register(**register_kwargs):

    def _register(obj):
        _container.register(obj, **register_kwargs)
        return obj

    return _register
