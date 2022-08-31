from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, TypeVar

from antidote import antidote_lib, inject, injectable, lazy, ScopeGlobalVar, world
from tests.utils import Box

T = TypeVar("T")


def test_files() -> None:
    world.include(antidote_lib)

    @injectable
    @dataclass
    class Files:
        __files: Dict[str, ScopeGlobalVar[str]] = field(default_factory=dict)
        __content: Dict[str, str] = field(default_factory=dict)

        @inject.method
        def read(self, filename: str) -> str:
            # Touching the ScopeGlobalVar by accessing it through world
            return self.__content[world[self.__files[filename]]]

        @inject.method
        def write(self, filename: str, content: str) -> None:
            path = self.__files.setdefault(
                filename, ScopeGlobalVar(default=filename, name=filename)
            )
            self.__content[filename] = content
            # Ensures scoped dependencies will be up-to-date
            path.set(filename)

    @lazy(lifetime="scoped")
    def length_of(filename: str, files: Files = inject.me()) -> Box[int]:
        return Box(len(files.read(filename)))

    @lazy(lifetime="scoped")
    def compare(a: str, b: str, files: Files = inject.me()) -> Box[bool]:
        return Box(files.read(a) == files.read(b))

    Files.write("a", "Hello World!")
    Files.write("b", "Hello World!")
    length = world[length_of("a")]
    assert length == Box(len("Hello World!"))
    assert world[length_of("a")] is length

    ab = world[compare("a", "b")]
    assert ab == Box(True)
    assert world[compare("a", "b")] is ab

    Files.write("a", "Changed")
    assert world[length_of("a")] == Box(len("Changed"))
    assert world[compare("a", "b")] == Box(False)
