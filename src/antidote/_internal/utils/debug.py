import base64
import inspect
import textwrap
from collections import deque
from typing import Deque, Hashable, List, Sequence, Tuple, TYPE_CHECKING

from .immutable import Immutable
from .. import API

if TYPE_CHECKING:
    from ...core.container import RawContainer

# Object will be allocated on the heap, so as close as possible to most user objects
# in memory.
_ID_MASK = id(object())


@API.private
def short_id(obj) -> str:
    """ Produces a short, human readable, representation of the id of an object. """
    n = id(obj) ^ _ID_MASK
    return (base64
            .b64encode(n.to_bytes(8, byteorder='little'))
            .decode('ascii')
            .rstrip('=')  # Remove padding
            .rstrip('A'))  # Remove 000000


@API.private
def debug_repr(x) -> str:
    from ..wrapper import is_wrapper
    try:
        return x.__antidote_debug_repr__()
    except AttributeError:
        pass
    if (isinstance(x, type) and inspect.isclass(x)) \
            or inspect.isfunction(x) \
            or is_wrapper(x):
        module = (x.__module__ + ".") if x.__module__ != "__main__" else ""
        return f"{module}{x.__qualname__}"
    return repr(x)


@API.private
def get_injections(func) -> Sequence:
    from ..wrapper import get_wrapper_dependencies
    try:
        return get_wrapper_dependencies(func)
    except TypeError:
        return []


@API.private
class DebugTreeNode(Immutable):
    __slots__ = ('info', 'singleton', 'children')
    info: str
    singleton: bool
    children: 'List[DebugTreeNode]'

    def __init__(self, info: str, *, singleton: bool = True,
                 children: 'List[DebugTreeNode]' = None):
        super().__init__(info=textwrap.dedent(info),
                         singleton=singleton,
                         children=children or [])


@API.private
class Task(Immutable):
    __slots__ = ()


@API.private
class DependencyTask(Task):
    __slots__ = ('dependency',)
    dependency: object


@API.private
class InjectionTask(Task):
    __slots__ = ('name', 'symbol', 'injections')
    symbol: str
    name: str
    injections: List[Hashable]


@API.private
def tree_debug_info(container: 'RawContainer',
                    origin,
                    depth: int = -1) -> str:
    from ...core.wiring import WithWiringMixin
    from ...core.exceptions import DependencyNotFoundError

    if depth < 0:
        depth = 1 << 31  # roughly infinity in this case.

    depth += 1  # To match root = depth 0
    root = DebugTreeNode(info=debug_repr(origin))
    original_root = root
    tasks: Deque[Tuple[DebugTreeNode, set, Task]] = deque([
        (root, set(), DependencyTask(origin))
    ])

    def add_root_injections(parent: DebugTreeNode, parent_dependencies: set, dependency):
        if isinstance(dependency, type) and inspect.isclass(dependency):
            cls = dependency
            conf = getattr(cls, '__antidote__', None)
            if conf is not None \
                    and isinstance(conf, WithWiringMixin) \
                    and conf.wiring is not None:
                for m in sorted(conf.wiring.methods):
                    if m != '__init__':
                        tasks.append((parent, parent_dependencies, InjectionTask(
                            name=f"Method: {m}",
                            injections=get_injections(getattr(cls, m)),
                        )))
        elif callable(dependency):
            for d in get_injections(dependency):
                tasks.append((parent, parent_dependencies, DependencyTask(d)))

    while tasks:
        parent, parent_dependencies, task = tasks.pop()
        if isinstance(task, DependencyTask):
            dependency = task.dependency
            try:
                debug = container.debug(dependency)
            except DependencyNotFoundError:
                if dependency is origin:
                    add_root_injections(parent, parent_dependencies, dependency)
                else:
                    parent.children.append(DebugTreeNode(f"/!\\ Unknown: "
                                                         f"{debug_repr(dependency)}"))

                continue

            if dependency in parent_dependencies:
                parent.children.append(DebugTreeNode(f"/!\\ Cyclic dependency: "
                                                     f"{debug.info}"))
                continue

            tree_node = DebugTreeNode(debug.info, singleton=debug.singleton)

            parent.children.append(tree_node)
            parent = tree_node
            parent_dependencies = parent_dependencies | {dependency}

            if dependency is origin:
                root = tree_node  # previous root is redundant
                add_root_injections(parent, parent_dependencies, dependency)

            if len(parent_dependencies) < depth:
                for d in debug.dependencies:
                    tasks.append((parent, parent_dependencies,
                                  DependencyTask(d)))
                for w in debug.wired:
                    if isinstance(w, type) and inspect.isclass(w):
                        for d in get_injections(getattr(w, '__init__')):
                            tasks.append((parent, parent_dependencies,
                                          DependencyTask(d)))
                    else:
                        tasks.append((parent, parent_dependencies, InjectionTask(
                            name=debug_repr(w),
                            injections=get_injections(w),
                        )))
        elif isinstance(task, InjectionTask) and task.injections:
            tree_node = DebugTreeNode(task.name)
            parent.children.append(tree_node)
            parent = tree_node
            for d in task.injections:
                tasks.append((parent, parent_dependencies, DependencyTask(d)))

    if not root.children and original_root is root:
        return f"{origin!r} is neither a dependency nor is anything injected."

    output = [
        ("* " if not root.singleton else "") + root.info
    ]
    nodes: Deque[Tuple[str, bool, DebugTreeNode]] = deque([
        ("", i == 0, child)
        for i, child in enumerate(root.children[::-1])
    ])
    any_not_singleton = not root.singleton

    while nodes:
        prefix, last, node = nodes.pop()
        any_not_singleton |= (not node.singleton)
        first_line, *rest = node.info.split("\n", 1)
        txt = prefix + ("└──" if last else "├──")
        txt += (" * " if not node.singleton else " ") + first_line
        new_prefix = prefix + ("    " if last else "│   ")
        if rest:
            txt += "\n" + textwrap.indent(rest[0], new_prefix)
        output.append(txt)

        for i, child in enumerate(node.children[::-1]):
            nodes.append((new_prefix, i == 0, child))

    output.append("")
    if any_not_singleton:
        output.extend(["* = not singleton",
                       ""])

    return "\n".join(output)
