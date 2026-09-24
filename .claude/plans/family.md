CLASS: a control drawn smaller than the 44 pt touch target

Instance: final Chrome audit (25 Sep): date pills From / To / Day you worked / Date measured 36 pt (e7b9b373e).

Sites:
- frontend/src/theme/glass-components.css .g-form-group .g-datefield input — same-root (44 pt box, pill drawn inside by 4 pt transparent borders)
- every other under-44 hit in the audit — not-affected: none remained (50 hits were all these four date fields)

Locked: the audit's under44 check (e2e/alpha6-audit.mjs).
