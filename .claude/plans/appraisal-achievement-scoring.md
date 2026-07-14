# Appraisal Scoring: Star Rating → (Actual/Target)×100

## Goal
Replace the manager **star rating** as the driver of Section A scores with measured
achievement `(actual / target) × 100`, **capped at 100%** (no reward for overachievement).
Applies to **both A1 (KRAs) and A2 (Competencies)**. The existing score-conversion
lookup table is **kept** — achievement maps to a 0–5 equivalent, then runs through the
same conversion pipeline.

## Core mechanic (the only conceptual change)
Per row, replace the rating source:

```
achievement       = (actual / target) × 100        # 0 if target is 0
capped_achievement = min(achievement, 100)          # cap overachievement at 100%
rating_value       = capped_achievement / 100 × 5   # 0–100% → 0–5 scale
```

Everything downstream is unchanged:
`weighted_sum → weighted_avg (1–5) → get_conversion_factor(table) → a1/a2_score`.

Sanity check: all rows at 100% achievement → weighted_avg 5.0 → factor 0.80 (Exceptional)
→ a1_score = (0.80/0.80)×70 = 70 (full marks). 85% across the board → 4.25 → 0.75 (Strong)
→ 65.6.

## Files to change

### 1. `hrms/hr/doctype/appraisal/appraisal.py`
- **`calculate_a1_score`** (~L200): keep the achievement calc; derive `rating_value` from
  `min(achievement,100)/100*5` instead of `manager_rating*5`. Rest untouched.
- **`calculate_a2_score`** (~L233): add per-row achievement calc for competencies
  (`actual/target*100`, 0 on zero target), then same achievement-derived `rating_value`.

### 2. `hrms/hr/doctype/appraisal_kra/appraisal_kra.json`
- Set `manager_rating` → `"hidden": 1` (no longer drives score; column kept for history).
- `achievement` stays visible (already `in_list_view`).

### 3. `hrms/hr/doctype/appraisal_functional_competency/appraisal_functional_competency.json`
- Add fields: `target` (Float), `actual` (Float), `achievement` (Float, read_only,
  in_list_view), mirroring the KRA table.
- Add them to `field_order`.
- Set `manager_rating` → `"hidden": 1`.

### 4. `hrms/hr/doctype/appraisal/appraisal.js`
- **`calculate_a1`** (~L331) and **`calculate_a2`** (~L353): mirror the Python —
  `rating_value` from capped achievement, not `manager_rating`.
- **`calculate_kra_row`** (~L565) / **`calculate_competency_row`** (~L612): compute
  `weighted_score`/`score` from capped achievement.
- **`calculate_achievement`** (~L576): after setting `achievement`, also recompute the
  row score and trigger `calculate_a1` (currently target/actual don't re-score).
- KRA `target`/`actual` handlers → recompute + `calculate_a1`.
- Add A2 competency handlers for `target`/`actual` → compute achievement + `calculate_a2`.
- `manager_rating` handlers become no-ops (or removed) for both tables.

### 5. `hrms/hr/doctype/appraisal/test_pms_changes.py` (TDD — red first)
- Rewrite `test_section_a_score_calculation` to drive `weighted_score` from `target/actual`.
- Update `test_pms_total_and_grade` and `test_final_score_uses_pms_total` to set
  `actual == target` for full marks instead of `manager_rating = 1.0`.
- **New** `test_overachievement_capped_at_100`: `actual=200, target=100` scores as 100%,
  not 200% — one row cannot inflate the section.
- **New** `test_a2_achievement_scoring`: competency scored via actual/target.
- Keep `test_achievement_calculation` / `test_zero_target_achievement` (still valid).

## Known follow-up (flagged, not silently shipped)
Existing A2 competency rows have no target data, so after migration they score 0% until
targets are entered. If A2 targets should come from a template/Competency default, that is
a **separate** enhancement — confirm whether to include or defer.

## Pipeline
1. TDD: update/add tests (red) → implement Python + JSON + JS (green).
2. `bench --site <site> migrate` to apply the new competency fields.
3. `bench --site <site> run-tests --module hrms.hr.doctype.appraisal.test_pms_changes`.
4. Auto-commit (`feat:`) → auto code-review → auto-deploy (Frappe `/deploy`).

## Not doing
- No change to Section B, demerits, leadership gate, grade scale, or the conversion table
  contents.
- Not deleting `manager_rating` columns (hidden, preserved for historical appraisals).
