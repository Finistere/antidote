from antidote._internal import API

_ABSTRACT_FLAG = '__antidote_abstract'


@API.private
class FinalMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        for b in bases:
            if isinstance(b, FinalMeta):
                raise TypeError(f"Type '{b.__name__}' cannot be inherited.")
        return super().__new__(mcls, name, bases, namespace)


@API.private
class AbstractMeta(type):
    def __new__(mcls, name, bases, namespace, **kwargs):
        abstract = kwargs.get('abstract')
        namespace[_ABSTRACT_FLAG] = abstract
        if not abstract:
            for b in bases:
                if isinstance(b, mcls) and not getattr(b, _ABSTRACT_FLAG):
                    raise TypeError(
                        f"Cannot inherit a service which is not defined abstract. "
                        f"Consider defining {b} abstract by adding 'abstract=True' as a "
                        f"metaclass parameter.")

        return super().__new__(mcls, name, bases, namespace)
