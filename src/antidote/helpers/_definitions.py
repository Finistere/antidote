from typing import Iterable, Optional, Union

from antidote import Tag
from antidote._internal.utils import SlotsReprMixin
from antidote.helpers.wire import Wiring


class Dependency(SlotsReprMixin):
    __slots__ = ('wiring', 'singleton', 'tags')

    def __init__(self,
                 wiring: Optional[Wiring],
                 singleton: bool,
                 tags: Optional[Iterable[Union[str, Tag]]]):
        self.wiring = wiring
        self.singleton = singleton
        self.tags = tags
