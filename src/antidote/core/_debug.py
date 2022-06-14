from __future__ import annotations

import collections.abc
import inspect
import textwrap
from collections import deque
from dataclasses import dataclass, field
from typing import Any, cast, Deque, List, Sequence, Tuple

from .._internal import API, debug_repr
from ._internal_catalog import InternalCatalog
from ._wrapper import is_wrapper, unwrap
from .data import DebugInfoPrefix, dependencyOf, LifeTime


@API.private
def get_injections(__func: Any) -> Sequence[object]:
    if isinstance(__func, type):
        __func = getattr(__func, "__init__")
    func = inspect.unwrap(__func, stop=is_wrapper)
    unwrapped = unwrap(func)
    if unwrapped is None:
        return []
    _, _, blueprint = unwrapped
    return [inj.dependency for inj in blueprint.injections if inj.dependency is not None]


@API.private
@dataclass(frozen=True)
class Task:
    parent: DebugTreeNode
    upstream_dependencies: frozenset[object]
    dependency: object
    prefix: str = field(default="")


@API.private
def scope_repr(lifetime: LifeTime | None) -> str:
    if lifetime is None:
        return " "
    else:
        return {
            LifeTime.TRANSIENT: " ∅ ",
            LifeTime.SCOPED: " ↻ ",
            LifeTime.SINGLETON: " 🟉 ",
        }[lifetime]


_LEGEND = f"""
{scope_repr(LifeTime.TRANSIENT)}= transient
{scope_repr(LifeTime.SCOPED)}= bound
{scope_repr(LifeTime.SINGLETON)}= singleton
"""


@API.private
@dataclass(frozen=True)
class DebugTreeNode:
    description: str
    lifetime: LifeTime | None
    children: List[DebugTreeNode] = field(default_factory=list)
    depth: int = 0

    def child(self, *, description: str, lifetime: LifeTime | None) -> DebugTreeNode:
        self.children.append(
            DebugTreeNode(
                description=description,
                lifetime=lifetime,
                depth=self.depth + 1,
            )
        )
        return self.children[-1]


@API.private
def tree_debug_info(catalog: InternalCatalog, origin: object, max_depth: int = -1) -> str:
    origin = dependencyOf[object](origin).wrapped

    if max_depth < 0:
        max_depth = 1 << 31  # roughly infinity in this case.

    root = DebugTreeNode(description=debug_repr(origin), lifetime=LifeTime.TRANSIENT)
    tasks: Deque[Task] = deque(
        [Task(parent=root, upstream_dependencies=frozenset(), dependency=origin)]
    )

    while tasks:
        task = tasks.popleft()
        debug = catalog.maybe_debug(task.dependency)
        # Using the private catalog after the first one.
        catalog = catalog.private
        if debug is None:
            injections = (
                get_injections(origin)
                if task.dependency is origin
                else cast(Sequence[object], tuple())
            )
            if injections:
                for injected in injections:
                    tasks.append(
                        Task(
                            parent=root,
                            upstream_dependencies=task.upstream_dependencies,
                            dependency=injected,
                        )
                    )
            else:
                child = task.parent.child(
                    description=f"/!\\ Unknown: {debug_repr(task.dependency)}", lifetime=None
                )
                if task.dependency is origin:
                    assert not tasks
                    return child.description
        elif task.dependency in task.upstream_dependencies:
            task.parent.child(
                description=f"/!\\ Cyclic dependency: {task.prefix}{debug.description}",
                lifetime=debug.lifetime,
            )
        else:
            child = task.parent.child(
                description=f"{task.prefix}{debug.description}", lifetime=debug.lifetime
            )
            if task.dependency is origin:
                root = child
            child_dependencies = task.upstream_dependencies | {task.dependency}

            if child.depth < max_depth:
                for dep in debug.dependencies:
                    tasks.append(
                        Task(
                            parent=child,
                            upstream_dependencies=child_dependencies,
                            prefix=dep.prefix if isinstance(dep, DebugInfoPrefix) else "",
                            dependency=dependencyOf(
                                dep.dependency if isinstance(dep, DebugInfoPrefix) else dep
                            ).wrapped,
                        )
                    )

                if isinstance(debug.wired, collections.abc.Sequence):
                    for w in debug.wired:
                        injections = get_injections(w)
                        if injections:
                            _child = child.child(
                                description=debug_repr(
                                    w.__init__ if isinstance(w, type) else w  # type: ignore
                                ),
                                lifetime=None,
                            )
                            for injected in injections:
                                tasks.append(
                                    Task(
                                        parent=_child,
                                        upstream_dependencies=child_dependencies,
                                        dependency=injected,
                                    )
                                )
                else:
                    injections = get_injections(debug.wired)
                    if injections:
                        for injected in injections:
                            tasks.append(
                                Task(
                                    parent=child,
                                    upstream_dependencies=child_dependencies,
                                    dependency=injected,
                                )
                            )

    output = [scope_repr(root.lifetime) + root.description]
    nodes: Deque[Tuple[str, bool, DebugTreeNode]] = deque(
        [("", i == 0, child) for i, child in enumerate(root.children[::-1])]
    )

    while nodes:
        prefix, last, node = nodes.pop()
        first_line, *rest = node.description.split("\n", 1)
        txt = prefix + ("└──" if last else "├──")
        txt += scope_repr(node.lifetime) + first_line
        new_prefix = prefix + ("    " if last else "│   ")
        if rest:
            txt += "\n" + textwrap.indent(rest[0], new_prefix)
        output.append(txt)

        for i, child in enumerate(node.children[::-1]):
            nodes.append((new_prefix, i == 0, child))

    output.append(_LEGEND)
    output[0] = output[0].lstrip()

    return "\n".join(output)
