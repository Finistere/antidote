import inspect

from antidote._internal import API
from .slots import SlotsMixin


@API.private
class ImmutableMeta(type):
    def __new__(mcls, name, bases, namespace, abstract: bool = False, copy: bool = True):
        if '__slots__' not in namespace:
            raise TypeError("Attributes must be defined in slots")
        slots = set(namespace['__slots__'])
        if any(name.startswith('__') for name in slots):
            raise ValueError("Private attributes are not supported.")

        if abstract:
            if len(slots) > 0:
                raise ValueError("Cannot be abstract and have a non-empty __slots__")
        else:
            if copy:
                if '__init__' in namespace and 'copy' not in namespace:
                    args = set(list(
                        inspect.signature(namespace['__init__']).parameters.keys()
                    )[1:])
                    if slots != args:
                        raise TypeError(f"__init__ must be defined with arguments"
                                        f" matching slots ({', '.join(sorted(slots))}) "
                                        f"not ({', '.join(sorted(args))})")
            else:
                namespace['copy'] = copy_not_supported

        return super().__new__(mcls, name, bases, namespace)


@API.private
def copy_not_supported(self):
    raise RuntimeError(f"Copy is not supported on {type(self)}")


@API.private
class Immutable(SlotsMixin, metaclass=ImmutableMeta, abstract=True):
    """
    Imitates immutable behavior by raising an exception when modifying an
    attribute through the standard means.
    """
    __slots__ = ()

    def __init__(self, **attrs):
        for attr, value in attrs.items():
            object.__setattr__(self, attr, value)

    def __setattr__(self, name, value):
        raise AttributeError(f"{type(self)} is immutable")


@API.private
class FinalImmutableMeta(ImmutableMeta):
    def __new__(mcls, name, bases, namespace, **kwargs):
        for b in bases:
            if isinstance(b, ImmutableMeta) \
                    and b.__module__ != __name__:
                raise TypeError(f"Type '{b.__name__}' cannot be inherited.")

        return super().__new__(mcls, name, bases, namespace, **kwargs)


@API.private
class FinalImmutable(Immutable, metaclass=FinalImmutableMeta, abstract=True):
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        # quick way to initialize an FinalImmutable through args.
        attrs = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        super().__init__(**attrs)