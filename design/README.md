# Glass design tokens

`tokens.json` is the **single source of truth** for the Glass design system. Values come only from `docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md` (§2, §4, §5, §6, §8) — change the spec first, then this file, never the other way around.

Three consumers are **generated** from this file and must never be hand-edited:

1. CSS custom properties (the Glass theme stylesheet)
2. A Tailwind theme fragment
3. Ionic `--ion-*` variables

## Regenerating

The generator does not exist yet (it arrives in a later step of the migration). Once it does: run it after **every** change to `tokens.json` and commit the regenerated outputs together with the change. Until then, no file in the repo is derived from this one.
