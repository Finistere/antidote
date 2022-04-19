import pytest

from antidote.core import Dependency
from antidote.core.getter import DependencyGetter


class Dummy(Dependency[object]):
    pass


def test_dependency_cannot_have_source():
    getter = DependencyGetter.raw(lambda dependency, default: dependency)
    with pytest.raises(TypeError):
        getter(Dummy(), source=lambda: object())
