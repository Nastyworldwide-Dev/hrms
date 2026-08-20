# Phase 3.5 — radius remap: what visibly changes

The Tailwind `borderRadius` scale moved from all-zero (the Modernist flat look)
onto the Glass ladder, per spec v1.3 §16.2. `none` (0) and `full` (9999px) are
unchanged, so anything already square-by-intent or pill-shaped is unaffected.

| Step | Was | Now | Glass ladder |
|---|---|---|---|
| `sm` | 0 | **6px** | `radius-pill` |
| `DEFAULT` | 0 | **9px** | `radius-well` |
| `md` | 0 | **9px** | `radius-well` |
| `lg` | 0 | **14px** | `radius-input` |
| `xl` | 0 | **17px** | `radius-card` |
| `2xl` | 0 | **20px** | `radius-panel` |
| `3xl` | 0 | **22px** | `radius-tabbar` |

Nothing else changed in the commit. No component, view, token or gate was
touched. Everything below is **recorded, not fixed** — see §4.

---

## 1. Count

**89 affected utility occurrences** across **51 files**.

| Where | Occurrences | Files |
|---|---|---|
| App source | **5** | 4 |
| `frappe-ui` components the app **renders** | 48 | 17 |
| `frappe-ui` components the app does **not** import | 36 | 30 |

`2xl` and `3xl` have **zero** occurrences anywhere — they are remapped for
consistency and for phase 5 to use, but nothing renders through them today.

**Correction to the 3.1 inventory.** That document reported "106 utilities
across 47 frappe-ui components". The real figure is **84 across 47 files**: the
earlier count included `rounded-full`, which this remap does not touch. The
file count was right; the utility count was 26% high.

**Two app "hits" were false positives**, excluded here and worth noting so the
next scan does not re-report them:
- `utils/formatters.js:37-38` — `const rounded = Math.round(…)`, a JavaScript
  variable, not a class.
- `components/glass/GAvatar.vue:6` — the word "rounded" in a doc comment.

---

## 2. Review checklist — surfaces that actually render

Grouped old → new. Everything here is reachable in the running app.

### 0 → 6px (`sm`)

| Surface | File |
|---|---|
| Text-editor content box, bottom corners (`rounded-b-sm`) | app `components/FormField.vue` |
| Calendar "show more" event chip | `frappe-ui` `Calendar/ShowMoreCalendarEvent.vue` |

### 0 → 9px (`DEFAULT` and `md`)

| Surface | File | × |
|---|---|---|
| Password submit button | app `views/ChangePassword.vue` | 1 |
| Password submit button | app `views/ForgotPassword.vue` | 1 |
| Autocomplete input + option rows | `frappe-ui` `Autocomplete.vue` | 3 |
| **Button — every variant and size** | `frappe-ui` `Button/Button.vue` | 6 |
| Calendar event block | `frappe-ui` `Calendar/CalendarEvent.vue` | 1 |
| Calendar event modal body | `frappe-ui` `Calendar/EventModalContent.vue` | 1 |
| Date picker input + popover | `frappe-ui` `DatePicker/DatePicker.vue` | 1 |
| Date **range** picker | `frappe-ui` `DatePicker/DateRangePicker.vue` | 3 |
| Date **time** picker | `frappe-ui` `DatePicker/DateTimePicker.vue` | 1 |
| Dropdown menu items | `frappe-ui` `Dropdown.vue` | 1 |
| Select control | `frappe-ui` `Select.vue` | 4 |
| Switch track | `frappe-ui` `Switch.vue` | 1 |
| Text input | `frappe-ui` `TextInput.vue` | 4 |
| Textarea | `frappe-ui` `Textarea.vue` | 4 |
| **Toast close button (20×20)** | `frappe-ui` `Toast.vue` | 1 |

### 0 → 14px (`lg`)

| Surface | File | × |
|---|---|---|
| Password sticky footer, top corners (`rounded-t-lg`) | app `views/ChangePassword.vue` | 1 |
| Password sticky footer, top corners (`rounded-t-lg`) | app `views/ForgotPassword.vue` | 1 |
| Autocomplete popover | `frappe-ui` `Autocomplete.vue` | 1 |
| Button — large variants | `frappe-ui` `Button/Button.vue` | 2 |
| Calendar event, expanded | `frappe-ui` `Calendar/CalendarEvent.vue` | 2 |
| Date picker popover | `frappe-ui` `DatePicker/DatePicker.vue` | 1 |
| Date range picker popover | `frappe-ui` `DatePicker/DateRangePicker.vue` | 1 |
| Date time picker popover | `frappe-ui` `DatePicker/DateTimePicker.vue` | 1 |
| Dropdown panel | `frappe-ui` `Dropdown.vue` | 1 |
| **Popover panel** — the shared floating surface | `frappe-ui` `Popover.vue` | 1 |
| **Toast body** | `frappe-ui` `Toast.vue` | 1 |

### 0 → 17px (`xl`)

| Surface | File | × |
|---|---|---|
| Button — extra-large variant | `frappe-ui` `Button/Button.vue` | 2 |
| **Dialog panel** | `frappe-ui` `Dialog.vue` | 1 |

### 0 → 20px / 22px (`2xl`, `3xl`)

Nothing renders through these today.

---

## 3. Where to look first

Four surfaces carry most of the visual weight, because they appear on many
screens rather than one:

1. **`Button/Button.vue`** — 10 occurrences across three steps. Every
   frappe-ui button in the app changes shape at once.
2. **`Popover.vue`** — the floating surface shared by Autocomplete, Dropdown,
   Select and both date pickers, so its 14px lands in several places at once.
3. **`Dialog.vue`** at 17px — and `GModal` already sets `--border-radius:
   var(--g-radius-panel)` (20px), so the two dialog systems now differ by 3px.
   Recorded, not reconciled.
4. **Toast** — body 14px, close button 9px, both visible on every toast.

The four Glass components that wrap or skin frappe-ui were built and reviewed
**against the zeroed scale**, so they are the highest-value spot-check:
`GLinkPicker` (Autocomplete), `GDatePicker` (DatePicker), `GToast` (Toast),
`GAvatar` (independent, but sits beside frappe-ui's Avatar).

---

## 4. Structurally wrong, not merely different

Four surfaces are **20 × 20 px boxes taking a 9px radius** — 45% of the box
dimension, which renders as a near-circle blob rather than a rounded square.
This is a genuine defect of the remap, not a taste call.

| Surface | File | Renders in this app? |
|---|---|---|
| Toast close button (`h-5 w-5 rounded`) | `frappe-ui` `Toast.vue` | **Yes** — every toast |
| List-filter count badge (`h-5 w-5 rounded`) | `frappe-ui` `ListFilter/ListFilter.vue` | No |
| Font-colour swatch (`h-5 w-5 rounded border`) | `frappe-ui` `TextEditor/FontColor.vue` | No |
| Font-colour swatch, second variant | `frappe-ui` `TextEditor/FontColor.vue` | No |

**Only the Toast close button matters today**; the other three sit in
components this app does not import. The fix, when someone takes it, is to
override that one control to `rounded-sm` (6px) or `rounded-full` in the Glass
toast skin — not to change the scale, which is correct for every other surface.

Not fixed here, per the prompt.

### Not a problem

- **No table element takes a radius.** Scanned for `<td>`/`<th>`/`<tr>`/`<table>`
  carrying a `rounded-*`; there are none, so `GDataTable` and the expense
  tables are unaffected.
- **No full-bleed container gains corners.** The only corner-specific uses are
  `rounded-t-lg` on two sticky footers, where rounding the top edge is the
  intended sheet idiom, and `rounded-b-sm` on an editor box.
- **The Glass ladder is untouched.** `rounded-panel`, `rounded-card`,
  `rounded-pill` and the rest still resolve through `--g-radius-*`; this remap
  only fills the generic scale that was zeroed.
