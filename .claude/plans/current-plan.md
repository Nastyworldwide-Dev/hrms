# Plan: Organizational Chart as a flow chart (owner, 28 Oct 2026: "build this and no need to be able to switch to list just only the flow chart version")

## GOAL
/org-chart reads like a flow chart, one person in focus: "N more above" pill → Direct manager box → focus box
→ team as 2-column boxes off one line (4, then See all) → Same manager folded. Flow chart only, no list view.
Approved mockup: ~/mockup-org-chart.html (flow chart, avatar "B · Black badge").

## OWNER DECISIONS (28 Oct 2026)
- Avatars: black badge, lime ring, white two letters, both themes (light "C" and dark "B" are the same badge).
  Tokens: --g-media-frame fill, --g-on-media-frame letters, --g-brand ring. Photo keeps the lime ring.
- Every chart box outlined: black (--g-ink) in light, lime (--g-accent-ink) in dark; focus box thicker.
- Initials: first two given-name words before bin/binti/a/l/a/p ("MH"). Top manager first, direct last.
- Empty said once: no "Team of N"/"No team" chip; dashed "No team yet"; "No manager set yet" box. No API change.

DESIGN SKILLS: NONE (existing frappe-ui screen built to the approved mockup with Glass tokens; impeccable/emil skills are not installed in this session)

## FLOW
OrgChart.vue → get_node() (unchanged) → utils/orgChart.chainLadder(chain_up) {direct, above (top first)}
→ template boxes; tap a box = focusPerson(id) (URL query, Back works, as today).

## MOCKUP: /home/qina/mockup-org-chart.html (approved by owner, 28 Oct 2026)

## COMMITS (one cause each)
0. test(words): "Organizational Chart" is a proper name on the sentence-case keep list (red on HEAD since c95c7285e).
1. feat(avatar): GAvatar `badge` — two letters, black disc, lime ring. utils/avatar.js initials() + tests.
2. feat(org-chart): flow chart layout in OrgChart.vue + chainLadder helper + updated template tests.

## EXPECTED OUTPUT
- yarn test: no new failures; biome check clean on changed files; design lint gate no new violations.
- Owner checks on phone after deploy (no local site has hrms).

## NOT DOING
- No list view, no whole-company tree, no new API fields. No deploy without the owner.

## Pipeline Summary
owner ask → mockup approved → plan (this) → TDD per commit → commit → review → push → owner deploys.
