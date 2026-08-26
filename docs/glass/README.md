# HR Frappe · Glass — documentation

Design authority for the HR PWA redesign on branch `nz-glass`.

## Read order

1. **`plan/THE_PLAN.md`** — **start here.** Everything remaining, in the order
   it should happen, rewritten 26 August after a week in which an employee found
   four defects we did not. Supersedes the ORDERING below; the design detail in
   GATE 2–4 still lives there.
2. **`plan/RELEASE_READINESS.md`** — The gates, their exit
   criteria, and what "live-ready" means measured rather than asserted. Says
   where the system actually stands and in what order to close the gap.
3. **`plan/HR_Glass_Phase_9_Work_Order.md`** — the *what*. The current work
   authority: locked decisions, measured evidence, the new material, all 62
   surfaces A to Z, eight phases, the coverage matrix, and the scope ruling on
   what "migrate off Frappe" means. Written to be worked from alone.
4. **`spec/HR_Frappe_Glass_Spec_v1.1.md`** — the build authority. Tokens, components, states, screens, accessibility, performance budget.
5. **`spec/HR_FRAPPE_Glass_Light_and_Dark_2.html`** — the mockup. Governs *values*, except the seven exceptions recorded in spec §14.4.
6. `plan/HR_Glass_Build_Plan_v1.md` — phases 0–8. Historical; superseded for
   current work by the phase 9 work order.

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

## frappe-ui version

`frappe-ui@0.1.105`, from npm, stated in `frontend/package.json` — which is now
the only place it is stated.

There used to be a `frappe-ui` submodule pinned at v0.1.278 alongside it, and a
paragraph here explaining that the app did not use it. The 0.1.278 upgrade was
attempted in phase 0, appeared to succeed because the build was green, and was
found in prompt 2.4 to have never taken effect. The submodule was deleted in
phase 9.1c rather than keep explaining it.

All Glass components were built against 0.1.105. Upgrading is deferred to its
own project — it is not part of the Glass migration.
