# SPDX-License: LGPL-3.0-or-later
# (c) 2024 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from typing import Callable
from contextlib import contextmanager
import FreeCAD as App  # type: ignore

try:
    from shiboken6 import isValid as ref_is_valid
except ImportError:
    from shiboken2 import isValid as ref_is_valid  # type: ignore # noqa: F401


def run_later(callback: Callable) -> None:
    from PySide.QtCore import QTimer  # type: ignore

    QTimer.singleShot(0, callback)


@contextmanager
def recompute_buffer(doc: App.Document | None = None, *, flush: bool = True):
    doc = doc or App.ActiveDocument
    if doc.RecomputesFrozen:
        yield
    else:
        try:
            doc.RecomputesFrozen = True
            yield
        except Exception:
            doc.RecomputesFrozen = False
            raise
        else:
            doc.RecomputesFrozen = False
            if flush:
                doc.recompute()
