# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

import FreeCAD as App  # type: ignore
from dataclasses import dataclass, field
import operator
from typing import ClassVar
from functools import total_ordering

translate = App.Qt.translate


def QT_TRANSLATE_NOOP(context, text):
    """This function does not translate the text but make it ready for translation"""
    return text


@total_ordering
@dataclass(slots=True, repr=False, eq=False)
class dtr:
    """Deferred translation. Translated when converted to str"""

    context: str
    source: str
    disambiguation: str | None = None
    num: int = -1

    _stable_hash: int = field(init=False)
    _as_tuple: ClassVar = operator.attrgetter("context", "source", "disambiguation", "num")

    def __post_init__(self):
        self._stable_hash = hash(dtr._as_tuple(self))

    def __repr__(self) -> str:
        return translate(*dtr._as_tuple(self))

    __str__ = __repr__

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other or self.source == other
        try:
            return dtr._as_tuple(self) == dtr._as_tuple(other)
        except Exception:
            return False

    def __lt__(self, other):
        return str(self) < str(other)

    def __hash__(self):
        return self._stable_hash
