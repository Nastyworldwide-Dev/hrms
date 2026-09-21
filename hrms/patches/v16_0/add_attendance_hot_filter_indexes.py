"""Indexes for the attendance domain's hot filters (v16_0).

Audit 21 Sep 2026 (D-H3, D-M11). One-shot call of the guard that also runs on
every migrate (hrms.utils.hot_indexes, hooks.after_migrate): the schema sync
drops a non-unique index led by a field without `search_index` whenever the
doctype JSON reloads, so the indexes are re-asserted after each sync rather
than trusted to a patch that runs once. Safe to re-run.
"""

from hrms.utils import hot_indexes


def execute():
	hot_indexes.ensure_hot_indexes()
