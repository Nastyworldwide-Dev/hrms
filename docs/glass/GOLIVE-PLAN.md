# Nadi Go-Live — Master Plan

**One truth:** we are stuck mid-parallel-run. The cutover hasn't happened.
Every "bug" is a link in ONE chain. Finish the cutover in order → the chain breaks.

---

## The chain (root → symptoms)

```
CUTOVER NOT DONE  (Nasty-Live still live, mirror read-only)
│
├─ mirrored rows are READ-ONLY (write-block)
│   ├─ HR can't fill missing fields  → shift_location empty → geofence fails (other branches)
│   │                                → user_id empty       → some check-ins fail
│   └─ approvers can't approve
│
├─ source has NO Nadi-native fields (shift_location, user_id)  → arrive empty
├─ source ≠ Nadi schema  → 11 schema gaps (un-ruled)
├─ files/photos NOT synced  → storage still only in ERP
└─ employees still use ERP  → check-ins land in ERP, dashboard/count looks wrong
```

**Nothing here is lost data.** It's incomplete + locked. Cutover completes + unlocks it.

---

## The guarantee against UNKNOWN bugs

We do NOT hunt bugs one by one. The senior already built the gate:

- **Schema Gaps** — finds every field/doctype/value the source has that Nadi doesn't.
- **Parity Check** — counts rows on both sides; flags any mismatch.
- **4 clean checks in a row** = cutover authorised.

**That gate IS "no unknown data bug."** The plan = make the gate green.

---

## Phase 1 — Readiness (surface everything, change nothing risky)

**Goal:** gate green — 0 un-ruled gaps, 4 clean parity checks.

1. **HR rules the 11 schema gaps** (guidance already given — 8 are "Not needed", E3 = Not needed, Advance/Interco = Fix-at-source or Not needed).
2. **Claude** builds a materializer: any gap ruled *"Add before cutover"* is added by code (exact source value — no guessing).
3. **Run parity** until 4 clean checks.

**Verify:** the instance banner reads "cutover ready", 0 outstanding rulings.

---

## Phase 2 — Complete the Nadi-native data

**Goal:** every employee has what the source could never provide.

- **shift_location** — per employee / per branch (drives geofence + shift rules).
- **user_id** — linked, FILL-EMPTY ONLY (never overwrite anyone who already reset).
- **storage** — photos/files migrated (the sync never carried these).

**Claude builds by code:** the fill-empty user_id guard; the storage puller.
**HR provides:** the shift_location values per branch (a sheet, or in-place after unlock).

**Verify:** no employee with empty shift_location; photos present; login works.

---

## Phase 3 — Cutover (break the chain at the root)

**Order is everything. Do NOT unlock before freezing.**

1. **Freeze Nasty-Live** — nobody writes there anymore. (Senior.)
2. **Final full sync** — capture the last state.
3. **Flip "Unlock Mirrored Writes."** — Nadi becomes the writer.
4. Everyone uses **Nadi Desk + PWA only.**

**This one step fixes:** approvals, check-in-to-Verifica, in-place editing — all at once.

**Verify:** approve a leave (works); check in on PWA (lands in Verifica); edit a mirrored employee (saves).

---

## Phase 4 — Safety net (your idea)

**Goal:** if data ever escapes to ERP again, rescue it — safely.

- **Auto-sync** (scheduled) — no HR button.
- **Non-destructive top-up mode** — FILL EMPTY, SKIP POPULATED, never overwrite.

**Claude builds by code.** Emergency-only after cutover; keeps Verifica current during any tail of the parallel run.

**Verify:** run it against a populated row → row unchanged; against an empty field → filled.

---

## Phase 5 — Smoke test + close

Walk one employee per branch through the whole loop:

- [ ] Check in / out → lands in Verifica, geofence correct
- [ ] Claim overtime → right type + hours shown
- [ ] Approver approves → works
- [ ] Dashboard count → honest number
- [ ] Photo + fields present

**Then:** disable the instance (or leave it as the frozen top-up source). Done.

---

## Who does what

| Claude (by code) | HR / Senior (in Desk / ops) |
|---|---|
| Schema-gap materializer | Rule the 11 gaps |
| user_id fill-empty guard | Freeze Nasty-Live |
| Storage puller | Flip Unlock (after freeze) |
| Auto-sync + top-up mode | Fill shift_location per branch |
| Dashboard-count fix | Run parity to 4 clean checks |

---

## The rule that prevents data bugs, always

**Fill empty. Skip populated. Never overwrite. Freeze before unlock.**
Every step above obeys it. That is the whole safety model.
