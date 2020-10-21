import inspect
import textwrap
from collections import deque
from typing import Deque, Hashable, List, Optional, Tuple, TYPE_CHECKING

from .immutable import Immutable
from .. import API

if TYPE_CHECKING:
    from ...core.container import RawContainer


@API.private
def debug_repr(x):
    try:
        return x.debug_repr()
    except AttributeError:
        pass
    if isinstance(x, type) and inspect.isclass(x) or callable(x):
        module = (x.__module__ + ".") if x.__module__ != "__main__" else ""
        return f"{module}{x.__qualname__}"
    return repr(x)


@API.private
def get_injections(func):
    from ..wrapper import get_wrapper_dependencies
    try:
        return get_wrapper_dependencies(func)
    except TypeError:
        return []


@API.private
class Symbol:
    default = "─"
    function = "f"
    method = "m"
    cycle = "/!\\"
    not_found = "404"
    lazy = "l"


@API.private
class DebugTreeNode(Immutable):
    __slots__ = ('info', 'symbol', 'singleton', 'children')
    symbol: str
    info: str
    singleton: bool
    children: 'List[DebugTreeNode]'

    def __init__(self, info: str, *, symbol: str = Symbol.default, singleton: bool = True,
                 children: 'List[DebugTreeNode]' = None):
        super().__init__(symbol=symbol, info=textwrap.dedent(info), singleton=singleton,
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
    __slots__ = ('name', 'symbol', 'dependencies')
    symbol: str
    name: str
    dependencies: List[Hashable]


@API.private
def tree_debug_info(container: 'RawContainer',
                    origin,
                    max_depth: int = 1 << 32,
                    helper_txt: bool = True) -> str:
    from ...core.wiring import WithWiringMixin
    from ...core.utils import DependencyDebug
    from ...providers.lazy import Lazy

    providers = container.providers
    fake_root = DebugTreeNode(symbol='', info='')
    tasks: Deque[Tuple[DebugTreeNode, set, Task]] = deque(
        [(fake_root, set(), DependencyTask(origin))])

    def maybe_debug(dependency) -> Optional[DependencyDebug]:
        for p in providers:
            debug = p.maybe_debug(dependency)
            if debug is not None:
                return debug

    def add_injections_tasks(parent: DebugTreeNode, parent_dependencies: set, dependency):
        if isinstance(dependency, type) and inspect.isclass(dependency):
            cls = dependency
            conf = getattr(cls, '__antidote__', None)
            if conf is not None and isinstance(conf, WithWiringMixin):
                if conf.wiring.methods == {'__init__'}:
                    for d in get_injections(getattr(cls, '__init__')):
                        tasks.append(
                            (parent, parent_dependencies,
                             DependencyTask(d)))
                else:
                    for m in sorted(conf.wiring.methods):
                        tasks.append((parent, parent_dependencies, InjectionTask(
                            symbol=Symbol.method,
                            name=m,
                            dependencies=get_injections(getattr(cls, m)),
                        )))
            for name in (n for n in dir(cls) if not n.startswith('__')):
                attr = getattr(cls, name)
                if isinstance(attr, Lazy):
                    debug = maybe_debug(attr)
                    assert debug is not None
                    import itertools
                    tasks.append((parent, parent_dependencies, InjectionTask(
                        symbol=Symbol.lazy,
                        name=f"{name} <{debug.info}>",
                        dependencies=set(itertools.chain(debug.dependencies, *(
                            get_injections(w) for w in debug.wired
                        ))) - {cls}
                    )))
        elif callable(dependency):
            f = dependency
            tasks.append((parent, parent_dependencies, InjectionTask(
                symbol=Symbol.function,
                name=debug_repr(f),
                dependencies=get_injections(f),
            )))

    while tasks:
        parent, parent_dependencies, task = tasks.pop()
        if isinstance(task, DependencyTask):
            dependency = task.dependency
            debug = maybe_debug(dependency)
            if debug is None:
                if parent_dependencies:
                    parent.children.append(
                        DebugTreeNode(debug_repr(dependency), symbol=Symbol.not_found))
                else:
                    add_injections_tasks(parent, parent_dependencies, dependency)

                continue

            if dependency in parent_dependencies:
                parent.children.append(DebugTreeNode(f"Cyclic dependency on {debug.info}",
                                                     symbol=Symbol.cycle))
                continue

            tree_node = DebugTreeNode(debug.info, singleton=debug.singleton)

            parent.children.append(tree_node)
            parent = tree_node
            parent_dependencies = parent_dependencies | {dependency}

            if len(parent_dependencies) < max_depth:
                for d in debug.dependencies:
                    tasks.append((parent, parent_dependencies,
                                  DependencyTask(d)))
                for w in debug.wired:
                    add_injections_tasks(parent, parent_dependencies, w)
        elif isinstance(task, InjectionTask) and task.dependencies:
            tree_node = DebugTreeNode(task.name, symbol=task.symbol)
            parent.children.append(tree_node)
            parent = tree_node
            if len(parent_dependencies) < max_depth:
                for d in task.dependencies:
                    tasks.append((parent, parent_dependencies, DependencyTask(d)))

    if not fake_root.children:
        return f"{origin!r} is neither a dependency nor is anything injected."

    root = fake_root.children[0]
    output = [root.info]
    nodes: Deque[(str, bool, DebugTreeNode)] = deque([
        ("", i == 0, child)
        for i, child in enumerate(root.children[::-1])
    ])

    while nodes:
        prefix, last, node = nodes.pop()
        first_line, *rest = node.info.split("\n", 1)
        txt = prefix + ("└─" if last else "├─") + node.symbol
        txt += (" *" if not node.singleton else " ") + first_line
        new_prefix = prefix + ("    " if last else "│   ")
        if rest:
            txt += "\n" + textwrap.indent(rest, new_prefix)
        output.append(txt)

        for i, child in enumerate(node.children[::-1]):
            nodes.append((new_prefix, i == 0, child))

    if helper_txt:
        output.append(textwrap.dedent(f"""
        * = not singleton
        ─{Symbol.function} = function
        ─{Symbol.method} = method
        ─{Symbol.lazy} = lazy
        """))
    return "\n".join(output)
