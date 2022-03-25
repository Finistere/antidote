import sys
from typing import Iterator, Optional, Union

import pytest

from antidote import factory, inject, QualifiedBy, service, world
from antidote.core.marker import Marker
from antidote.exceptions import DependencyNotFoundError


@pytest.fixture(autouse=True)
def setup_world() -> Iterator[None]:
    with world.test.new():
        yield


class GlobalService:
    pass


def test_marker_me():
    @service
    class MyService:
        pass

    @inject
    def f(my_service: MyService = inject.me()):
        return my_service

    assert f() is world.get[MyService]()


def test_invalid_marker_me_missing_dependency():
    class MyService:
        pass

    @inject
    def f(my_service: MyService = inject.me()):
        return my_service

    # Should not fail before.
    with pytest.raises(DependencyNotFoundError):
        f()


def test_invalid_marker_me_wrong_type_hint():
    with pytest.raises(TypeError, match=r"(?i).*inject\.me.*"):
        @inject
        def f(my_service=inject.me()):
            return my_service

    with pytest.raises(TypeError, match=r"(?i).*inject\.me.*"):
        @inject
        def g(my_service: int = inject.me()):
            return my_service


def test_marker_me_from():
    class MyService:
        pass

    @factory
    def create_service() -> MyService:
        return MyService()

    @inject
    def f(my_service: MyService = inject.me(source=create_service)):
        return my_service

    assert f() is world.get(MyService, source=create_service)


def test_invalid_marker_me_from_wrong_type_hint():
    class MyService:
        pass

    @factory
    def create_service() -> MyService:
        return MyService()

    with pytest.raises(TypeError, match=r"(?i).*inject\.me.*"):
        @inject
        def f(my_service=inject.me(source=create_service)):
            return my_service

    with pytest.raises(TypeError, match=r"(?i).*inject\.me.*"):
        @inject
        def g(my_service: int = inject.me(source=create_service)):
            return my_service

    class OtherService:
        pass

    with pytest.raises(TypeError, match=r"(?i).*does not match.*"):
        @inject
        def h(my_service: OtherService = inject.me(source=create_service)):
            return my_service


def test_invalid_marker_me_from_argument_mix():
    class MyService:
        pass

    @factory
    def create_service() -> MyService:
        return MyService()

    with pytest.raises(TypeError, match="(?i).*additional arguments.*"):
        @inject
        def f(x: MyService = inject.me(source=create_service, qualified_by=object())):
            pass

    with pytest.raises(TypeError, match="(?i).*additional arguments.*"):
        @inject
        def f2(x: MyService = inject.me(QualifiedBy(object()), source=create_service)):
            pass


def test_marker_get():
    @service
    class MyService:
        pass

    @inject
    def f(my_service=inject.get(MyService)):
        return my_service

    assert f() is world.get[MyService]()


def test_invalid_marker_get_missing_dependency():
    class MyService:
        pass

    @inject
    def f(my_service=inject.get(MyService)):
        return my_service

    # Should not fail before.
    with pytest.raises(DependencyNotFoundError):
        f()


def test_marker_from_get():
    class MyService:
        pass

    @factory
    def create_service() -> MyService:
        return MyService()

    @inject
    def f(my_service=inject.get(MyService, source=create_service)):
        return my_service

    assert f() is world.get(MyService, source=create_service)


def test_invalid_marker_from_get_wrong_target():
    class MyService:
        pass

    @factory
    def create_service() -> MyService:
        return MyService()

    class OtherService:
        pass

    with pytest.raises(TypeError, match=r"(?i).*does not match.*"):
        @inject
        def f(my_service: OtherService = inject.me(source=create_service)):
            return my_service


def test_custom_marker():
    class CustomMarker(Marker):
        pass

    with pytest.raises(TypeError, match="(?i).*custom marker.*"):
        @inject
        def test(test=CustomMarker()):
            pass


def test_marker_me_optional():
    service(GlobalService)

    @inject
    def f(my_service: Optional[GlobalService] = inject.me()):
        return my_service

    assert f() is world.get[GlobalService]()

    with world.test.empty():
        assert f() is None

    @inject
    def f2(my_service: Union[GlobalService, None] = inject.me()):
        return my_service

    assert f2() is world.get[GlobalService]()

    with world.test.empty():
        assert f2() is None

    if sys.version_info >= (3, 10):
        @inject
        def f3(my_service: 'GlobalService | None' = inject.me()):
            return my_service

        assert f3() is world.get[GlobalService]()

        with world.test.empty():
            assert f3() is None


def test_marker_me_optional_source():
    class MyService:
        pass

    @factory
    def create_service() -> MyService:
        return MyService()

    @inject
    def f(my_service: Optional[MyService] = inject.me(source=create_service)):
        return my_service

    assert f() is world.get(MyService, source=create_service)

    with world.test.empty():
        assert f() is None
