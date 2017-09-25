from .container import Container
import wrapt

_container = Container()


def inject(**inject_kwargs):

    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        args, kwargs = _container._builder.instantiate(wrapped, args, kwargs,
                                                       **inject_kwargs)
        return wrapped(*args, **kwargs)

    return wrapper


def register(**register_kwargs):

    def _register(obj):
        _container.register(obj, **register_kwargs)
        return obj

    return _register
