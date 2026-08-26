# Rendering the audit screens

The findings in `../frontend-audit.md` come from these images. To re-shoot them
after a fix, run the same two scripts.

> **These are the UNMASKED set — the one to cite.** `capture.mjs` shoots the app
> exactly as a user sees it. The visual gate's baselines live separately in
> `design/baselines/` and hide every `data-visual-mask` element, so dynamic
> strings are blank in those. The two were one directory until 26 August 2026;
> see `design/baselines/README.md` for why they were split.
>
> Until `capture.mjs` is next run against a served site, the 114 files here named
> `*-390-dark`, `*-390-light` and `*-1440-dark` are still the masked copies the
> gate left behind. The other 228 are correct.

## 1. Serve the app

```bash
cd verify-bench/sites
../env/bin/python -m frappe.utils.bench_helper frappe --site fresh.local serve --port 8080
```

The site's `apps/hrms` symlinks to this repo, so `yarn build` in `frontend/` is
what the browser sees. Rebuild before capturing, or you audit a stale bundle.

## 2. Seed content (once per site)

Mock content hides the CONTENT class of bug, so the audit runs against a long
Malaysian name, an 80-row leave list, real check-ins and a Malaysian holiday list.

```bash
cd verify-bench/sites
AUDIT_PW='<pick one>' ../env/bin/python -c "
import frappe; frappe.init(site='fresh.local'); frappe.connect()
exec(open('<repo>/docs/glass/audit/seed.py').read())"
```

Creates employee `HR-EMP-00001` — *Nurul Aisyah binti Abdul Rahman* — and logs in
as `nurul.aisyah@nastyworldwide.com`.

**Seeding artifacts, not defects:** leave rows show `0d` because validation is
bypassed so `total_leave_days` is never computed, and balance bars sit at 100%
because no approved leave is deducted.

## 3. Capture

```bash
cd frontend
AUDIT_PW='<same>' node ../docs/glass/audit/capture.mjs
```

273 captures / 351 files into `screens/`, plus `manifest.json` with per-capture
console errors. `ONLY=home,more node …` limits the run to named slugs.

Variants: 390×844 @2× dark/light (each with a scroll-bottom shot), 390 dark
reduce-transparency, 768 dark/light, 1440 dark/light.

## Known gaps in coverage

`/hr/issues` silently redirects to the staff view without an HR role — the two
captures are byte-identical. KPI, the Team roster, populated Remote approvals and
the expense claim list need data or a role this employee does not have. The design
specimen is `import.meta.env.DEV` only and is absent from a production build.
