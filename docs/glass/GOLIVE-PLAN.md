# Nadi — Consolidated Plan (one source of truth)

**One truth:** we're mid-parallel-run. Most "bugs" are one chain from an unfinished
cutover. The code bugs are fixed. What's left = a few tweaks + tooling + the cutover.

**The rules that keep everything safe:**
- Fill empty · skip populated · never overwrite · **freeze before unlock**.
- Anchor on the **shift**, not the calendar day.

---

## TRACK 1 — Code fixes

### ✅ Done + pushed (nz-glass)
- Notification stranding
- Permission fence (identity)
- **Overtime = total worked − shift length** (late-in no longer wrongly counted)
- Naming numbers self-heal (couldn't create employee)
- Replacement-leave ratio → HR-configurable
- Overtime + Replacement Leave → one "Claim Overtime or Leave" button
- Check-out geofence honest + sharpest-GPS fix
- OT form v1 (shows claim type + hours)

### 🛠️ To build
1. **Overnight / next-day checkout** *(removes HR's "check out before 11:59pm" workaround)*
   - Rule: a clock-OUT closes the employee's OPEN clock-in's shift — **even next calendar day.**
   - Anchor = shift + clock-in. Early clock-in = "early", shift decides the window.
   - Standard ERPNext has the same gap → we **enhance**, not borrow.

2. **OT form v2** *(refine what we shipped)*
   - **Claimed hours = auto-populated, read-only** (from punch-verified OT). No manual typing.
   - **Reason = REQUIRED** type-in field. *(reversal: re-add it, make it mandatory.)*
   - **Remove attachments.**
   - Employee eligibility (Pay/Leave) shown **read-only** (from HR setting). *(mostly done.)*

3. **Dashboard employee count = 0** — cosmetic count fix (data IS there).

---

## TRACK 2 — Migration tooling (by code, safe, waits for cutover)

- **Schema-gap materializer** — any gap ruled "Add" is created by code, exact source value.
- **Auto-sync + non-destructive top-up** — scheduled; fill-empty, skip-populated, never overwrite.
- **user_id fill-empty guard** — link logins without ever overwriting anyone who reset.
- **Storage / photo puller** — the sync never carried files; bring them by code.

*None of these touch live data. They wait for your rulings + the cutover.*

---

## TRACK 3 — Cutover (HR / senior + me)

| Phase | Do | Who |
|---|---|---|
| 1. Readiness | Rule the 11 schema gaps (8 = "Not needed", E3 = Not needed); run parity → 4 clean checks | HR |
| 2. Complete data | Fill shift_location per branch; user_id (fill-empty); migrate photos | HR + me |
| 3. Cutover | **Freeze Nasty-Live → final sync → flip Unlock** | Senior + HR |
| 4. Safety net | Turn on auto-sync + non-destructive top-up | me |
| 5. Smoke test | One employee per branch: check in/out, claim OT, approve, dashboard | HR |

**Phase 3 alone fixes the 4 Critical items** (check-in loss, approver blocked, geofence, login) — all at once.

---

## Order of execution (what happens when)

1. **Now — me, in parallel (zero live-data risk):**
   Overnight-checkout fix · OT form v2 · dashboard count · the Track-2 tooling.
2. **Now — you/HR:** rule the 11 gaps.
3. **When ready — cutover:** freeze → sync → unlock → complete data → smoke test.
4. **After:** sync becomes emergency-only (non-destructive top-up).

---

## The 4 Critical (all one cutover)

| Critical issue | Resolves at |
|---|---|
| Check-in data loss / lands in ERP | cutover |
| Missing Shift Location → geofence fails at branches | cutover |
| user_id not linked → login + check-in fail | cutover |
| Approver can't approve | cutover |

**Not 4 problems. One cutover.**
