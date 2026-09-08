"""An in-memory stand-in for frappe.qb, so Script Report SQL can run bench-free.

Script Reports build pypika queries and `.run()` them; neither pypika nor a
database is on the gate's interpreter. This fake accepts the subset the HR
reports use — DocType tables, column predicates (==, !=, <, <=, >, >=, isin,
isnull/isnotnull, &, |), select with star / columns / Case / Sum / Count,
join().on(), where, orderby, groupby, limit, distinct, run(as_dict / pluck)
— and evaluates it against rows given to `install(tables)`.

It is deliberately small and literal: a query shape it does not understand
raises, so a test cannot pass by accident. Rows are plain dicts; a join merges
the joined row into the base row (base wins on a name collision).

    import _qb_stub
    _qb_stub.install({"Salary Slip": [dict(name="SS-1", company="A", ...)]})
"""

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from datetime import date
from unittest.mock import MagicMock

_TABLES: dict[str, list[dict]] = {}


class Predicate:
	def __init__(self, fn: Callable[[dict], bool]):
		self.fn = fn

	def __and__(self, other):
		return Predicate(lambda row: self.fn(row) and other.fn(row))

	def __or__(self, other):
		return Predicate(lambda row: self.fn(row) or other.fn(row))

	def __invert__(self):
		return Predicate(lambda row: not self.fn(row))

	def __call__(self, row):
		return self.fn(row)


class Column:
	def __init__(self, table: str, name: str):
		self.table, self.name, self.alias = table, name, None

	def value(self, row):
		return row.get(self.name)

	def as_(self, alias):
		clone = Column(self.table, self.name)
		clone.alias = alias
		return clone

	def _cmp(self, other, op):
		# the operand may be another column (a join's ON clause) or a literal
		def test(row):
			left = row.get(self.name)
			right = other.value(row) if hasattr(other, "value") else other
			# the database coerces a date literal against a date column; so do we
			if isinstance(left, date) and isinstance(right, str):
				right = date.fromisoformat(right[:10])
			elif isinstance(right, date) and isinstance(left, str):
				left = date.fromisoformat(left[:10])
			if op in ("lt", "le", "gt", "ge") and (left is None or right is None):
				return False
			if op == "eq":
				return left == right
			if op == "ne":
				return left != right
			if op == "lt":
				return left < right
			if op == "le":
				return left <= right
			if op == "gt":
				return left > right
			return left >= right

		return Predicate(test)

	def __eq__(self, other):
		return self._cmp(other, "eq")

	def __ne__(self, other):
		return self._cmp(other, "ne")

	def __lt__(self, other):
		return self._cmp(other, "lt")

	def __le__(self, other):
		return self._cmp(other, "le")

	def __gt__(self, other):
		return self._cmp(other, "gt")

	def __ge__(self, other):
		return self._cmp(other, "ge")

	def isin(self, values):
		values = list(values)
		return Predicate(lambda row: row.get(self.name) in values)

	def notin(self, values):
		values = list(values)
		return Predicate(lambda row: row.get(self.name) not in values)

	def isnull(self):
		return Predicate(lambda row: row.get(self.name) is None)

	def isnotnull(self):
		return Predicate(lambda row: row.get(self.name) is not None)

	def between(self, low, high):
		return Predicate(lambda row: low <= row.get(self.name) <= high)

	__hash__ = object.__hash__


class Star:
	def __init__(self, table):
		self.table = table


class Table:
	def __init__(self, name):
		self._name = name

	def __getattr__(self, name):
		if name == "star":
			return Star(self._name)
		if name.startswith("_"):
			raise AttributeError(name)
		return Column(self._name, name)

	def __getitem__(self, name):
		return Column(self._name, name)


class Case:
	def __init__(self):
		self.branches: list[tuple[Predicate, object]] = []
		self.default = None
		self.alias = None

	def when(self, predicate, value):
		self.branches.append((predicate, value))
		return self

	def else_(self, value):
		self.default = value
		return self

	def as_(self, alias):
		self.alias = alias
		return self

	def value(self, row):
		for predicate, value in self.branches:
			if predicate(row):
				return value.value(row) if hasattr(value, "value") else value
		return self.default.value(row) if hasattr(self.default, "value") else self.default


class Aggregate:
	def __init__(self, kind, expr):
		self.kind, self.expr, self.alias = kind, expr, None

	def as_(self, alias):
		self.alias = alias
		return self

	def over(self, rows):
		if self.kind == "count":
			return len(rows)
		return sum((self.expr.value(row) or 0) for row in rows)


def Count(expr):
	return Aggregate("count", expr)


def Sum(expr):
	return Aggregate("sum", expr)


def Extract(*args, **kwargs):
	raise NotImplementedError("Extract is not modelled by _qb_stub")


class Criterion:
	@staticmethod
	def all(predicates):
		predicates = list(predicates)
		return Predicate(lambda row: all(p(row) for p in predicates))

	@staticmethod
	def any(predicates):
		predicates = list(predicates)
		return Predicate(lambda row: any(p(row) for p in predicates))


class Query:
	def __init__(self, table: Table):
		self.table = table
		self.columns: list = []
		self.predicates: list[Predicate] = []
		self.joins: list[tuple[Table, Predicate]] = []
		self._pending_join: Table | None = None
		self._limit = None

	def select(self, *columns):
		self.columns.extend(columns)
		return self

	def where(self, predicate):
		self.predicates.append(predicate)
		return self

	def join(self, table):
		self._pending_join = table
		return self

	def left_join(self, table):
		return self.join(table)

	def on(self, predicate):
		self.joins.append((self._pending_join, predicate))
		self._pending_join = None
		return self

	def orderby(self, *args, **kwargs):
		return self

	def groupby(self, *args):
		return self

	def distinct(self):
		return self

	def limit(self, n):
		self._limit = n
		return self

	def _rows(self):
		rows = [dict(r) for r in _TABLES.get(self.table._name, [])]
		for table, on in self.joins:
			joined = []
			for base in rows:
				for other in _TABLES.get(table._name, []):
					merged = {**other, **base}
					if on(merged):
						joined.append(merged)
			rows = joined
		rows = [r for r in rows if all(p(r) for p in self.predicates)]
		return rows[: self._limit] if self._limit else rows

	def run(self, as_dict=False, pluck=None, **kwargs):
		rows = self._rows()
		if any(isinstance(c, Aggregate) for c in self.columns):
			record = {}
			for c in self.columns:
				key = getattr(c, "alias", None) or getattr(c, "name", None) or c.kind
				record[key] = c.over(rows) if isinstance(c, Aggregate) else None
			return [_dict(record)] if as_dict else [tuple(record.values())]
		out = []
		for row in rows:
			record = {}
			for c in self.columns:
				if isinstance(c, Star):
					record.update(row)
				else:
					record[c.alias or c.name] = c.value(row)
			out.append(record)
		if pluck:
			# pluck=True takes the first selected column, as frappe does
			key = pluck if isinstance(pluck, str) else next(iter(out[0]), None) if out else None
			return [r.get(key) for r in out]
		return [_dict(r) for r in out] if as_dict else [tuple(r.values()) for r in out]


class _dict(dict):
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError as exc:
			raise AttributeError(key) from exc

	def __setattr__(self, key, value):
		self[key] = value


class QB:
	desc = "desc"
	asc = "asc"

	def DocType(self, name):
		return Table(name)

	def from_(self, table):
		return Query(table)

	class terms:
		Case = Case
		Criterion = Criterion


def install(tables: dict[str, list[dict]] | None = None):
	"""Point frappe.qb (and the query-builder imports) at the in-memory tables."""
	import frappe

	_TABLES.clear()
	_TABLES.update({k: [dict(r) for r in v] for k, v in (tables or {}).items()})
	frappe.qb = QB()

	def _module(name, **names):
		module = types.ModuleType(name)
		module.__path__ = []  # a package, so submodule imports resolve
		module.__getattr__ = lambda _name: MagicMock()  # names the tests never reach
		module.__dict__.update(names)
		sys.modules[name] = module
		return module

	query_builder = _module(
		"frappe.query_builder",
		Case=Case,
		Criterion=Criterion,
		Order=types.SimpleNamespace(desc="desc", asc="asc"),
		DocType=QB().DocType,
	)
	query_builder.functions = _module("frappe.query_builder.functions", Count=Count, Sum=Sum, Extract=Extract)
	query_builder.custom = _module("frappe.query_builder.custom")

	pypika = types.ModuleType("pypika")
	pypika.Field = Column
	terms = types.ModuleType("pypika.terms")
	terms.Criterion = Criterion
	pypika.terms = terms
	sys.modules.setdefault("pypika", pypika)
	sys.modules.setdefault("pypika.terms", terms)
	return frappe.qb


def rows(table: str) -> list[dict]:
	return _TABLES.get(table, [])
