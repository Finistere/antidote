from __future__ import annotations

import base64
import inspect
import textwrap
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, List, Optional, Set, Tuple, TYPE_CHECKING

from .immutable import Immutable
from .. import API

if TYPE_CHECKING:
    from ...core.container import RawContainer, Scope

# Object will be allocated on the heap, so as close as possible to most user objects
# in memory.
_ID_MASK = id(object())


@API.private
def short_id(__obj: object) -> str:
    """Produces a short, human readable, representation of the id of an object."""
    n = id(__obj) ^ _ID_MASK
    return (
        base64.b64encode(n.to_bytes(8, byteorder="little"))
        .decode("ascii")
        .rstrip("=")  # Remove padding
        .rstrip("A")
    )  # Remove 000000


@API.private
def debug_repr(__obj: object) -> str:
    from ..wrapper import is_wrapper

    try:
        return str(__obj.__antidote_debug_repr__())  # type: ignore
    except Exception:
        pass
    if isinstance(__obj, type) or inspect.isfunction(__obj) or is_wrapper(__obj):
        if isinstance(__obj.__module__, str) and __obj.__module__ not in {"__main__", "builtins"}:
            module = __obj.__module__ + "."
        else:
            module = ""
        return f"{module}{__obj.__qualname__}"  # type: ignore
    return repr(__obj)


@API.private
def get_injections(__func: Any) -> List[object]:
    from ..wrapper import get_wrapper_injections, is_wrapper

    try:
        wrapped_func = inspect.unwrap(__func, stop=lambda f: is_wrapper(f))
        return list(get_wrapper_injections(wrapped_func).values())
    except TypeError:
        return []


@API.private
class Task:
    pass


@API.private
@dataclass
class DependencyTask(Task):
    dependency: object
    prefix: str = field(default="")


@API.private
@dataclass
class InjectionTask(Task):
    name: str
    injections: List[object]


@API.private
def scope_repr(scope: "Optional[Scope]", *, empty: str) -> str:
    from ...core import Scope

    if scope is None:
        return "<∅> "
    elif scope is Scope.singleton() or scope is Scope.sentinel():
        return empty
    else:
        return f"<{scope.name}> "


_LEGEND = """
Singletons have no scope markers.
<∅> = no scope (new instance each time)
<name> = custom scope
"""


@API.private
def tree_debug_info(container: "RawContainer", origin: object, max_depth: int = -1) -> str:
    from ...core.wiring import WithWiringMixin
    from ...core.exceptions import DependencyNotFoundError
    from ...core import Scope
    from ...core.utils import DebugInfoPrefix

    @API.private
    class DebugTreeNode(Immutable):
        __slots__ = ("info", "scope", "children", "depth")
        info: str
        scope: Optional[Scope]
        children: List[DebugTreeNode]
        depth: int

        def __init__(
            self,
            info: str,
            *,
            depth: int = 0,
            scope: Optional[Scope] = Scope.sentinel(),
            children: Optional[List[DebugTreeNode]] = None,
        ) -> None:
            super().__init__(textwrap.dedent(info), scope, children or [], depth)

        def child(self, info: str, *, scope: Optional[Scope] = Scope.sentinel()) -> DebugTreeNode:
            self.children.append(
                DebugTreeNode(
                    info,
                    depth=self.depth + 1,
                    scope=scope,
                )
            )
            return self.children[-1]

    if max_depth < 0:
        max_depth = 1 << 31  # roughly infinity in this case.

    root = DebugTreeNode(debug_repr(origin))
    original_root = root
    tasks: Deque[Tuple[DebugTreeNode, Set[object], Task]] = deque(
        [(root, set(), DependencyTask(origin))]
    )

    def add_root_injections(
        parent: DebugTreeNode, parent_dependencies: Set[object], dependency: object
    ) -> None:
        from ...core.wiring import Methods

        if isinstance(dependency, type):
            cls = dependency
            conf = getattr(cls, "__antidote__", None)
            if conf is not None and isinstance(conf, WithWiringMixin) and conf.wiring is not None:
                if isinstance(conf.wiring.methods, Methods):
                    for name, member in cls.__dict__.items():
                        if name != "__init__" and callable(member):
                            injections = get_injections(member)
                            if injections:
                                tasks.append(
                                    (
                                        parent,
                                        parent_dependencies,
                                        InjectionTask(
                                            name=f"Method: {name}",
                                            injections=injections,
                                        ),
                                    )
                                )
                else:
                    for name in sorted(conf.wiring.methods):
                        if name != "__init__":
                            tasks.append(
                                (
                                    parent,
                                    parent_dependencies,
                                    InjectionTask(
                                        name=f"Method: {name}",
                                        injections=get_injections(getattr(cls, name)),
                                    ),
                                )
                            )
        elif callable(dependency):
            for d in get_injections(dependency):
                tasks.append((parent, parent_dependencies, DependencyTask(d)))

    while tasks:
        parent, parent_dependencies, task = tasks.popleft()
        if isinstance(task, DependencyTask):
            dependency = task.dependency
            try:
                debug = container.debug(dependency)
            except DependencyNotFoundError:
                if dependency is origin:
                    add_root_injections(parent, parent_dependencies, dependency)
                else:
                    parent.child(f"/!\\ Unknown: {debug_repr(dependency)}")

                continue

            if dependency in parent_dependencies:
                parent.child(f"/!\\ Cyclic dependency: {task.prefix}{debug.info}")
                continue

            child = parent.child(f"{task.prefix}{debug.info}", scope=debug.scope)
            child_dependencies = parent_dependencies | {dependency}

            if child.depth < max_depth:
                for d in debug.dependencies:
                    if isinstance(d, DebugInfoPrefix):
                        tasks.append(
                            (
                                child,
                                child_dependencies,
                                DependencyTask(prefix=d.prefix, dependency=d.dependency),
                            )
                        )
                    else:
                        tasks.append(
                            (child, child_dependencies, DependencyTask(prefix="", dependency=d))
                        )
                for w in debug.wired:
                    if isinstance(w, type):
                        for d in get_injections(getattr(w, "__init__")):
                            tasks.append((child, child_dependencies, DependencyTask(d)))
                    else:
                        tasks.append(
                            (
                                child,
                                child_dependencies,
                                InjectionTask(
                                    name=debug_repr(w),
                                    injections=get_injections(w),
                                ),
                            )
                        )

                if dependency is origin:
                    root = child  # previous root is redundant
                    add_root_injections(child, child_dependencies, dependency)

        elif isinstance(task, InjectionTask) and task.injections:
            child = parent.child(task.name)
            for d in task.injections:
                tasks.append((child, parent_dependencies, DependencyTask(d)))

    if not root.children and original_root is root:
        return f"{origin!r} is neither a dependency nor is anything injected."

    output = [scope_repr(root.scope, empty="") + root.info]
    nodes: Deque[Tuple[str, bool, DebugTreeNode]] = deque(
        [("", i == 0, child) for i, child in enumerate(root.children[::-1])]
    )

    while nodes:
        prefix, last, node = nodes.pop()
        first_line, *rest = node.info.split("\n", 1)
        txt = prefix + ("└──" if last else "├──")
        txt += scope_repr(node.scope, empty=" ") + first_line
        new_prefix = prefix + ("    " if last else "│   ")
        if rest:
            txt += "\n" + textwrap.indent(rest[0], new_prefix)
        output.append(txt)

        for i, child in enumerate(node.children[::-1]):
            nodes.append((new_prefix, i == 0, child))

    output.append(_LEGEND)

    return "\n".join(output)
