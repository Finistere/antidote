from typing import Callable, Optional, TypeVar, Union

import pytest
from typing_extensions import Annotated

from antidote import From, FromArg, Get, Provide
from antidote._internal.argspec import Arguments
from antidote.core._annotations import (
    AntidoteAnnotation,
    extract_annotated_arg_dependency,
    extract_annotated_dependency,
    extract_auto_provided_arg_dependency,
)
from antidote.core.marker import Marker

T = TypeVar("T")


class Dummy:
    pass


class DummyLegacySource:
    def __rmatmul__(self, other):
        assert other is Dummy
        return DummyLegacySource


def test_invalid_from_arg():
    with pytest.raises(TypeError, match=".*function.*"):
        FromArg(object())


@pytest.mark.parametrize(
    "type_hint,expected",
    [
        pytest.param(
            type_hint,
            expected,
            id=str(type_hint).replace("typing.", "").replace(f"{__name__}.", ""),
        )
        for type_hint, expected in [
            (Annotated[Dummy, object()], None),
            (Dummy, None),
            (str, None),
            (T, None),
            (Union[str, Dummy], None),
            (Union[str, Dummy, int], None),
            (Optional[Union[str, Dummy]], None),
            (Callable[..., Dummy], None),
            (Provide[Dummy], Dummy),
            (Annotated[Dummy, From(DummyLegacySource())], DummyLegacySource),
            (Annotated[Dummy, FromArg(lambda arg: arg.name * 2)], "xx"),
            (Annotated[Dummy, Get("something")], "something"),
        ]
    ],
)
def test_extract_explicit_arg_dependency(type_hint, expected):
    def f(x: type_hint):
        pass

    arguments = Arguments.from_callable(f)
    assert extract_annotated_arg_dependency(arguments[0]) == expected

    def g(x: type_hint = None):
        pass

    arguments = Arguments.from_callable(g)
    assert extract_annotated_arg_dependency(arguments[0]) == expected


@pytest.mark.parametrize(
    "type_hint,expected",
    [
        pytest.param(
            type_hint,
            expected,
            id=str(type_hint).replace("typing.", "").replace(f"{__name__}.", ""),
        )
        for type_hint, expected in [
            (Dummy, Dummy),
            (Annotated[Dummy, object()], Dummy),
            (str, None),
            (T, None),
            (Union[str, Dummy], None),
            (Union[str, Dummy, int], None),
            (Optional[Union[str, Dummy]], None),
            (Callable[..., Dummy], None),
            (Provide[Dummy], None),
            (Annotated[Dummy, From(DummyLegacySource())], None),
            (Annotated[Dummy, FromArg(lambda arg: arg.name * 2)], None),
            (Annotated[Dummy, Get("something")], None),
        ]
    ],
)
def test_extract_auto_provided_arg_dependency(type_hint, expected):
    def f(x: type_hint):
        pass

    arguments = Arguments.from_callable(f)
    assert extract_auto_provided_arg_dependency(arguments[0]) == expected

    def g(x: type_hint = None):
        pass

    arguments = Arguments.from_callable(g)
    assert extract_auto_provided_arg_dependency(arguments[0]) == expected


@pytest.mark.parametrize(
    "type_hint,expected",
    [
        pytest.param(
            type_hint,
            expected,
            id=str(type_hint).replace("typing.", "").replace(f"{__name__}.", ""),
        )
        for type_hint, expected in [
            (Provide[Dummy], Dummy),
            (Annotated[Dummy, object()], Dummy),
            (str, str),
            (T, T),
            (Union[str, Dummy], Union[str, Dummy]),
            (Annotated[Dummy, From(DummyLegacySource())], DummyLegacySource),
            (Annotated[Dummy, Get("something")], "something"),
        ]
    ],
)
def test_extract_annotated_dependency(type_hint, expected):
    assert extract_annotated_dependency(type_hint) == expected


def test_multiple_antidote_annotations():
    type_hint = Annotated[Dummy, Get("dummy"), Get("dummy")]

    def f(x: type_hint):
        pass

    arguments = Arguments.from_callable(f)
    with pytest.raises(TypeError):
        extract_annotated_arg_dependency(arguments[0])

    with pytest.raises(TypeError):
        extract_annotated_dependency(type_hint)


def test_unknown_antidote_annotations():
    type_hint = Annotated[Dummy, AntidoteAnnotation()]

    def f(x: type_hint):
        pass

    arguments = Arguments.from_callable(f)
    with pytest.raises(TypeError):
        extract_annotated_arg_dependency(arguments[0])

    with pytest.raises(TypeError):
        extract_annotated_dependency(type_hint)


def test_antidote_annotation_with_marker():
    type_hint = Annotated[Dummy, Get("dummy")]

    def f(x: type_hint = Marker()):
        pass

    arguments = Arguments.from_callable(f)
    with pytest.raises(TypeError, match="(?i).*Marker.*with.*annotation.*"):
        extract_annotated_arg_dependency(arguments[0])


@pytest.mark.parametrize(
    "type_hint",
    [
        pytest.param(
            type_hint, id=str(type_hint).replace("typing.", "").replace(f"{__name__}.", "")
        )
        for type_hint in [Annotated[Dummy, FromArg(lambda arg: arg.name * 2)]]
    ],
)
def test_argument_only_annotations(type_hint):
    with pytest.raises(TypeError):
        extract_annotated_dependency(type_hint)
