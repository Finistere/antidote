import pytest

from antidote._internal.utils import raw_getattr


def test_raw_getattr():
    class A:
        @staticmethod
        def static():
            return 'static'

        @classmethod
        def klass(cls):
            return 'klass'

        def method(self):
            return 'method'

    class B(A):
        pass

    for (cls, with_super) in [(A, False), (B, True)]:
        method = raw_getattr(cls, 'static', with_super)
        assert method is not None
        assert isinstance(method, staticmethod)

        method = raw_getattr(cls, 'klass', with_super)
        assert method is not None
        assert isinstance(method, classmethod)

        method = raw_getattr(cls, 'method', with_super)
        assert method is not None
        assert method(1) == 'method'

        with pytest.raises(AttributeError, match=".*unknown.*"):
            raw_getattr(cls, 'unknown', with_super)
