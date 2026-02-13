# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

# ruff: noqa: S608

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from sqlite3 import Connection, connect
from typing import Any, TYPE_CHECKING
from Part import Shape  # type: ignore

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable


@contextmanager
def transaction(path: str | Path) -> Generator[Connection, None, None]:
    try:
        con = connect(str(path))
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


@contextmanager
def connection(path: str | Path) -> Generator[Connection, None, None]:
    try:
        con = connect(str(path))
        yield con
    finally:
        con.close()


def in_params(params: list[Any]) -> str:
    return ",".join("?" * len(params))


def lower_trim_list(items: list[str] | str) -> list[str]:
    if isinstance(items, str):
        return lower_trim_list(items.split(","))
    return [s for s in (v.strip().lower() for v in items) if s]


@dataclass
class SvgEntity:
    """Persistent Topological Shape"""

    id: str
    tag: str
    label: str
    path: str
    href: str | None = None
    brep: str | None = None

    @cached_property
    def shape(self) -> Shape:
        shape = Shape()
        shape.importBrepFromString(self.brep, False)  # noqa: FBT003
        return shape


class SvgDatabase:
    """Svg Database"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        with transaction(self.path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS objects (
                    id text,
                    tag text,
                    label text,
                    path text not null primary key,
                    href text,
                    brep text
                );
            """)

            con.execute("""
                CREATE INDEX IF NOT EXISTS
                    objects_ident
                    ON objects(id);
            """)

            con.execute("""
                CREATE INDEX IF NOT EXISTS
                    objects_tag
                    ON objects(tag);
            """)

            con.execute("""
                CREATE INDEX IF NOT EXISTS
                    objects_label
                    ON objects(label);
            """)

    def _query(self, sql: str, params: list[Any] | None = None) -> list[SvgEntity]:
        with connection(self.path) as con:
            if params is None:
                cursor = con.execute(sql)
            else:
                cursor = con.execute(sql, params)
            return [SvgEntity(*cols) for cols in cursor.fetchall()]

    def find_by_pattern(
        self,
        patterns: list[str] | str,
        field: str,
        include_brep: bool = True,
    ) -> list[SvgEntity]:
        params = (re.sub(r"%+", "\\%", s) for s in lower_trim_list(patterns))
        params = (re.sub(r"_+", "\\_", s) for s in params)
        params = [s.replace("*", "%") for s in params]
        valid_fields = {
            "tag": "tag",
            "id": "id",
            "label": "label",
            "path": "path",
            "group": "group",
        }

        brep = ", brep" if include_brep else ""

        field = valid_fields.get(field, "id")
        if field == "group":
            field = "path"
            params = [f"%/{g}/%" for g in params]

        individual = f"""
            SELECT id, tag, label, path, href {brep}
            FROM objects
            WHERE {field} LIKE ? ESCAPE '\\'
            """  # nosec B608

        subquery = " UNION ALL ".join(
            [individual] * len(params),
        )
        return self._query(
            f"SELECT sq.* FROM ({subquery}) sq ORDER BY sq.path",  # nosec B608
            params,
        )

    def find_by_tag(self, tags: list[str] | str, include_brep: bool = True) -> list[SvgEntity]:
        return self.find_by_pattern(tags, "tag", include_brep)

    def find_by_group(self, groups: list[str] | str, include_brep: bool = True) -> list[SvgEntity]:
        return self.find_by_pattern(groups, "group", include_brep)

    def find_by_id(self, ids: list[str] | str, include_brep: bool = True) -> list[SvgEntity]:
        return self.find_by_pattern(ids, "id", include_brep)

    def find_by_label(self, labels: list[str] | str, include_brep: bool = True) -> list[SvgEntity]:
        return self.find_by_pattern(labels, "label", include_brep)

    def find_by_path(self, path: str, include_brep: bool = True) -> list[SvgEntity]:
        return self.find_by_pattern([path], "path", include_brep)

    def find_all(self, include_brep: bool = True) -> list[SvgEntity]:
        brep = ", brep" if include_brep else ""
        return self._query(
            f"""
            SELECT id, tag, label, path, href {brep}
            FROM objects
            ORDER BY path
            """,  # nosec B608
        )

    def add(self, entity: SvgEntity) -> None:
        with transaction(self.path) as con:
            self._add(entity, con)

    def _add(self, entity: SvgEntity, con: Connection) -> None:
        con.execute(
            """
            INSERT INTO objects (id, tag, label, path, href, brep)
            VALUES (?,?,?,?,?,?)
            """,
            (
                entity.id,
                entity.tag,
                entity.label,
                entity.path,
                entity.href,
                entity.brep,
            ),
        )

    @contextmanager
    def add_many(self) -> Generator[Callable[[SvgEntity], None], None, None]:
        with transaction(self.path) as con:

            def add(entity: SvgEntity) -> None:
                self._add(entity, con)

            yield add

    def add_many_iter(self, entities: Iterable[SvgEntity]) -> None:
        with transaction(self.path) as con:
            for e in entities:
                self._add(e, con)
