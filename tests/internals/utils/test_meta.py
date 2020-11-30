import pytest

from antidote._internal.utils.immutable import FinalImmutableMeta
from antidote._internal.utils.meta import AbstractMeta, FinalMeta


def test_abstract_meta():
    class A(metaclass=AbstractMeta):
        pass

    with pytest.raises(TypeError, match="abstract"):
        class B(A):
            pass

    class C(metaclass=AbstractMeta, abstract=True):
        pass

    class D(C):
        pass

    with pytest.raises(TypeError, match="abstract"):
        class E(D):
            pass


@pytest.mark.parametrize('meta', [FinalMeta, FinalImmutableMeta])
def test_final_meta(meta):
    class Mixin:
        pass

    class Dummy(Mixin, metaclass=meta):
        __slots__ = ()

    with pytest.raises(TypeError):
        class SubDummy(Dummy):
            __slots__ = ()
