# HR Frappe · Glass — documentation

Design authority for the HR PWA redesign on branch `nz-glass`.

## Read order

1. **`plan/HR_Glass_Build_Plan_v1.md`** — start here. Phases, prompt sequence, gate decisions, risks.
2. **`spec/HR_Frappe_Glass_Spec_v1.1.md`** — the build authority. Tokens, components, states, screens, accessibility, performance budget.
3. **`spec/HR_FRAPPE_Glass_Light_and_Dark_2.html`** — the mockup. Governs *values*, except the seven exceptions recorded in spec §14.4.

## Authority

| Question | Answer |
|---|---|
| Spec and mockup disagree on a value? | Mockup wins |
| Mockup fails an accessibility criterion in spec §14? | Spec wins — see §14.4 |
| Anything else? | Spec v1.1 |

`retired/HR_FRAPPE_Glass_Implementation_Spec__1_.html` is **v1.0 and superseded**. Do not build from it. Kept only so the v1.1 change log in §0 can be traced.

## Reference

Background reasoning. Read when a decision looks arbitrary.

| File | Answers |
|---|---|
| `Mockup_Spec_Reconciliation.md` | Why v1.1 differs from v1.0 |
| `Modernist_to_Glass_Reuse_Map.md` | What to reuse, reskin or replace, per file |
| `External_Materials_Survey_Glass.md` | Library choices; the frappe-ui upgrade case |
| `Liquid_Glass_Direction_Note.md` | Design rationale; the fidelity ceiling |
| `HR_Glass_Research_Addendum_nz-version-16.md` | Audit against this branch |
| `HR_Glass_Implementation_Research_v1.md` | Original audit — baseline was upstream, see the addendum |

## `decisions/`

One short file per gated decision: context, options, choice, who signed off. Six are open at the time of writing — see build plan §1.1.
