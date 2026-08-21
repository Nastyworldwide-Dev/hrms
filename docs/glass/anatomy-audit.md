# Anatomy audit — every §12 screen against what it renders

Audit only. Nothing was changed. Spec v1.7, audited 21 August 2026, after the
Login rebuild in 7.2.

Checked three things per screen: **stack order**, **element presence**, and
whether the layout **is the anatomy** or **the original structure re-skinned** —
the failure mode Login exhibited, where Glass components were dropped into a
two-panel layout the anatomy never described.

## Verdict

| Screen | Verdict |
|---|---|
| **Sign in** | Follows — rebuilt in 7.2 |
| **Check in** | Follows — divergences recorded in v1.5 |
| **Issues** (staff) | Follows |
| **Issue board** (HR) | Follows — anatomy written from the screen in v1.6 |
| **Leave** | **Diverges, not recorded** |
| **Home** | **Diverges, not recorded** |
| **Attendance** | **Diverges, not recorded** |
| **KPI** | Recorded divergences hold; one more not recorded |
| **Overtime** | **Diverges, not recorded** — and not a layout problem |

---

## 1. The Login pattern repeats on three screens

Home, Leave and Attendance are each **re-skinned inside a two-column desktop
layout** that no anatomy describes:

| Screen | Layout | What sits in the second column |
|---|---|---|
| `Home.vue` | `lg:grid-cols-2` | `RequestPanel`, behind an `lg:border-l` |
| `leave/Dashboard.vue` | `lg:grid-cols-[1fr_280px]` | holidays |
| `attendance/Dashboard.vue` | `lg:grid-cols-[1.1fr_1fr]` | actions and request lists |

Their **mobile** stacks largely match their anatomies, so the divergence is
invisible below `lg:` — which is why three batches passed over it. §20.3 defines
the content column as `max-width: 720px`, **left-aligned against the sidebar**:
one column. Nothing in §20 authorises a screen splitting in two at desktop, and
the spec's only mention of a two-panel layout is v1.7's entry recording that
Login's was stock Frappe HR and was removed.

**Not recorded anywhere.** Whether these three are a defect or an unwritten
desktop pattern is a ruling, not an implementation detail: a 280px sidebar
column beside a 720px content column is a different information design from the
single stack §20.3 describes.

## 2. Overtime — the anatomy has no purchase on the screen

`ot/OTRequestForm.vue` renders through `FormView` with
`:fields="formFields.data"`, fetched from `hrms.api.get_doctype_fields`. **The
field order is the server's doctype configuration, not the anatomy.** §12
specifies:

> date field → hours field → eligibility note panel → explanation field (66px)
> → primary → routing caption

The screen renders whatever the doctype returns, in the order it returns it.
Two consequences:

- **`GNotePanel` has zero consumers app-wide** — only `DesignSpecimen` imports
  it. §10.2 #22's eligibility hint, which the anatomy places on this screen,
  does not exist in the running app.
- **All eight form screens share this property.** Overtime is the only one with
  a §12 anatomy, so it is the only one where the mismatch is visible, but the
  mechanism is identical everywhere.

This is the deepest finding in the audit. Every other divergence is a layout
decision; this one means an anatomy cannot be satisfied by styling at all —
it would need the field order to move into the client, or the anatomy to
describe what a doctype-driven form actually is.

## 3. Attendance — stack order wrong on mobile too

Actual mobile order, from the `order-*` classes:

```
1  calendar (+ stat panel, inside AttendanceCalendar)
2  primary — REQUEST ATTENDANCE
3  recent attendance requests
4  upcoming shifts
6  action list (3 rows)          ← anatomy puts this at position 4
6  recent shift requests
7  …
```

The anatomy is calendar → stat panel → primary → **action list** → request
lists. The action list sits after two request lists instead. Introduced in 5.3:
the three ghost buttons were flattened into one panel **in place**, rather than
moved to the anatomy's position.

**A latent bug beside it:** two blocks both carry `order-6` and `order-5` is
unused on mobile, so their relative order is decided by DOM position rather
than intent. Any future insertion between them changes the screen silently.

## 4. Smaller unrecorded divergences

**Home** renders `PendingApprovalsBanner` *above* the entire status block. The
anatomy's "banner if unresolved punch" is a different element — the
forgot-to-check-out strip inside `CheckInPanel` — and that one **is** correctly
placed, immediately after the last-punch caption. So this is an extra element,
not a mis-ordering.

**KPI** carries year and cycle filter selects above the score panel that the
anatomy does not include. Its recorded divergences (no goals panel, no verdict
line, richer KRA rows) all still hold.

---

## Caveat on method

This audit reads rendered stack order from the templates, not from a running
browser. For Attendance in particular the CSS `order` values mean DOM order and
visual order differ — that finding is inferred from the classes, not observed,
and belongs on the device-review list with the rest of §18.
