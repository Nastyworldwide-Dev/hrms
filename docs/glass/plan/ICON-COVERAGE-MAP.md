# Icon coverage map (plan slice S3)

Measured 22 Sep 2026 against **lucide-static@latest — 1848 icons**, fetched and
counted, not quoted from documentation.

S3 is a doc and nothing else. It exists to answer one question before S4 installs
anything: *does every icon this app renders today have a target in Lucide?* If
the answer were no, S4 would be a redraw, not a rename, and the plan would need
re-approval. The answer is yes, with two names that need a decision rather than a
lookup. Those two are decided below.

## Why replace feather at all

`feather-icons` 4.29.2: last upstream commit 11 Mar 2025, last publish 1 May
2024, 287 icons. Not a criticism of the library — it is simply finished. Lucide
is its maintained fork: ISC, a first-party Vue package, per-icon exports that
tree-shake, and near-identical names.

The size case is not the main one but it is real, and measured:

| | raw | gzipped |
|---|---|---|
| all 287 feather icons (what ships today) | 52.5 KB | **10.5 KB** |
| the names actually rendered | 1.6 KB | **0.6 KB** |
| 14 hand-rolled components | 6.9 KB | — |

All 287 ship regardless of use. `frappe-ui`'s `FeatherIcon.vue` does
`import feather from 'feather-icons'` and then reads `Object.keys(feather.icons)`
at module scope for its prop validator, so the whole namespace is retained. That
is not a bundler setting we can change from here; it is what the dependency does.

**S4 must record the real gzip delta and revert if it is not negative.** The
projection is about −14 KB gz. A projection is not a measurement.

## Correction to the earlier inventory

An earlier progress note recorded "13 feather names across 6 files". That was
wrong: it counted literal `name="..."` only. **36 names are rendered across 28
files.** Three call sites bind the name dynamically, and all three resolve to
literals in the code — `WorkflowActionSheet.vue:89,94` (`x`, `check`),
`Home.vue:70-107` (`link.icon`, which is a component, not a feather name), and
`RequestActionSheet.vue` (`plus`/`check`, `alert-triangle`/`clock`). No name is
computed from server data, so the migration set is closed and knowable.

## Coverage: 36 rendered names

- **29 identical** — the name works unchanged in Lucide.
- **5 renamed**, all mechanical:

| feather | lucide |
|---|---|
| `alert-triangle` | `triangle-alert` |
| `check-circle` | `circle-check` |
| `check-square` | `square-check` |
| `edit` | `pen-line` |
| `edit-2` | `pencil` |

- **2 with no same-name target**, decided here rather than guessed:

| feather | decision | why |
|---|---|---|
| `filter` (`ListView.vue:25`) | **`funnel`** | Lucide offers `funnel` and `list-filter`. `funnel` is the solid funnel outline feather drew; `list-filter` is three stacked lines, a different idea. `ListView` filters a list, so the temptation is `list-filter` — take `funnel` anyway, because it is the glyph users of this app already learned. |
| `trash-2` (`RequestActionSheet.vue:93`) | **`trash`** | `trash-2` is not a Lucide icon name; it survives only as a back-compat alias. Two sibling files (`ExpensesTable.vue:108`, `ExpenseTaxesTable.vue:100`) already use plain `trash` for the same destructive action, so this **unifies** a split the app had. |

`lucide-vue-next` does still export `Filter`, `Trash2`, `AlertTriangle`,
`CheckCircle`, `Edit` and `Edit2` as aliases — verified in its published `.d.ts`.
S4 will **not** use them. An alias keeps a dead vocabulary alive in a codebase
that just paid to replace it.

## The 14 hand-rolled components

All 14 have a Lucide target, so `src/components/icons/` can go entirely.

| component | lucide |
|---|---|
| `ApprovaIcon` | `circle-check-big` |
| `AttendanceIcon` | `user-check` |
| `ExpenseIcon` | `receipt` |
| `ExternalLinkIcon` | `external-link` |
| `HelpdeskIcon` | `headphones` |
| `HomeIcon` | `house` |
| `KPIIcon` | `chart-line` |
| `LeaveIcon` | `calendar-days` |
| `MoreIcon` | `ellipsis` |
| `ProjectBoardIcon` | `kanban` |
| `ShiftIcon` | `calendar-clock` |
| `SopIcon` | `book-open-text` |
| `SupportIcon` | `life-buoy` |
| `TeamIcon` | `users` |

These are the nav and Home quick-link glyphs — the most-seen icons in the app.
Each row above is a **proposal, not a measurement**: it is judgement about which
Lucide glyph carries the same meaning, and a few (`kanban` for a project board,
`life-buoy` for support) change the drawing noticeably even though the meaning
holds. They are listed here so the change is reviewable before it lands, not
discovered afterwards.

## Inline SVG (slice S5, not S4)

34 inline `<svg>` across 29 files in 10 directories — 14 of them are the icon
components above. The rest are in `components/glass/` (5),
`components/` (2: `SideNav`, `AttendanceCalendar`), `glass/` headers (2:
`GAppHeader`, `GSearchBar`) and seven views. Not audited for Lucide equivalence
here: several are not icons at all (a progress ring, an upload target), so S5
must triage before it converts.

## What is still owed

- The gzip delta, measured on a real production build (S4's revert condition).
- One library on the page, not two: S4 removes `feather-icons` in the same commit
  that adds Lucide, or it has made the bundle worse.
