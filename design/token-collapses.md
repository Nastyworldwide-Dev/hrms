# Token collapses: why each accepted pair is accepted

`design/gates/tokens.mjs` reports every pair of `--g-*` tokens that are identical in one
theme and different in the other. The swap of one for the other is invisible in the theme
where they match, so a wrong token can ship unseen (the `bg-accent` defect hid that way).
`design/token-collapse-baseline.json` lists the 19 accepted pairs. It has no reason field,
so the reasons live here. Review of 7 Oct 2026 (slice S9). No token value was changed.

Verdicts:

- **a** BY DESIGN: the two tokens are one Apple system colour in that theme. Kept.
- **b** RISK: two different roles that share a value. A swap would be a real bug in the
  other theme. Kept; the table says whether any code already swaps them.
- **c** SHOULD SPLIT: none. No pair has clear evidence that the values should differ.

The surface family (page `bg`, `sheet-bg`, `surface`, `glass-fill-fallback`, `sheet-cell`)
mirrors iOS: the same white or grouped grey in light, and a second "elevated" step in
dark (page #000, card #1C1C1E, sheet ground #1C1C1E, sheet cell #2C2C2E). Sharing a
light value is Apple's own palette. The risk is only in dark, where a card token used
inside a sheet lands on the sheet's own colour and disappears.

| Pair | Theme | Verdict | Reason | Misuse found |
|---|---|---|---|---|
| bg / sheet-bg | light | b | Page ground and sheet ground are both #F2F2F7 in light; dark is #000 vs #1C1C1E. A page ground used inside a sheet paints a black slab in dark only. | yes: components/StrictRejectionDialog.vue:3 (`bg-bg` inside GModal), components/ExpenseTaxesTable.vue:65 (`bg-ground` inside GModal), components/WorkflowActionSheet.vue:7 (`bg-ground` bar, view=actionSheet, rendered inside RequestActionSheet in a GModal). Should be `bg-sheet-bg`. Question: views/Approvals.vue:740 `.g-approvals__bar` is a page bar that uses `--g-sheet-bg`; `--g-bg` if it is meant to be page ground (dark #1C1C1E bar on #000 may be intended). |
| brand / accent-ink | dark | b | Spec 2.4: accent TEXT on dark is the brand colour itself, so they match in dark by spec. In light brand (#C8FF00) must never set type or a mark (1.18:1 on white). This is the original bg-accent defect. | yes: theme/glass-components.css:3939 `.g-linkpick__tick` colours the picked-option check with `var(--g-brand)` in both themes; on a light cell it is 1.18:1. Should be `var(--g-accent-ink)`. Checked and fine: 744 and 1766 are dark-scoped; 519 and 3382 use accent-ink on purpose; ring arc, map ring and checked boxes use brand as a fill or rule. |
| glass-fill-fallback / sheet-bg | dark | b | Content-cell fill and sheet ground are both #1C1C1E in dark. A cell inside a sheet has no edge against it. `.g-sheet .g-form-group/.g-list/.g-sheet__group` are overridden to `sheet-cell` (glass-components.css:4734); other cell rules are not. | yes: theme/glass-components.css:5125 `.g-attachment` (rendered inside the request sheet, components/RequestActionSheet.vue:65) is not in the 4734 override list; components/ExpenseTaxesTable.vue:253 (`.expense-fields` inputs, inside a GModal). Should be `--g-sheet-cell` inside a sheet. |
| glass-fill-fallback / sheet-cell | light | b | Cell on a page and cell in a sheet are both #FFFFFF in light (iOS secondarySystemGroupedBackground); dark is #1C1C1E vs #2C2C2E. Same two sites as the row above are the swap. | yes: same as the row above (glass-components.css:5125, ExpenseTaxesTable.vue:253). No `sheet-cell` use on a page. |
| glass-fill / hair | dark | b | Panel fill and row divider are both white at 7.5% in dark (spec 2/6). Different roles: area fill vs 1px line. Light is .56 white vs 8% ink. | no: `--g-hair` is only used for 1px rules, dividers and grid lines; `--g-glass-fill` only on the tab bar and side nav panels. |
| on-badge / glass-fill-fallback | light | b | `on-badge` is a theme-constant white (count text on the red badge); the cell is white only in light. | no: `--g-on-badge` is used once, the tab-bar badge count (glass-components.css:241). |
| on-badge / ink | dark | b | Constant white vs primary text, which is white only in dark. In light ink is near-black, which would be unreadable on the red badge. | no: same single use. |
| on-badge / sheet-cell | light | b | As above, white vs the sheet cell. | no |
| on-badge / surface | light | b | As above, white vs the card surface. | no |
| sheet-bg / surface | dark | b | Sheet ground and card surface are both #1C1C1E in dark. A `bg-surface` control inside a sheet disappears into it (contrast 1.00); in light it reads white on #F2F2F7. | yes: components/FormattedField.vue:28 (`bg-surface` read-only text block, shown inside RequestActionSheet), views/team/TeamRoster.vue:132 and :140 (`bg-surface` date inputs inside the Assign shift GModal). Should be `bg-sheet-cell`. |
| sheet-cell / surface | light | b | Cell in a sheet and card on a page are both #FFFFFF in light; dark is #2C2C2E vs #1C1C1E. Same swap as the row above. | yes: same sites (FormattedField.vue:28, TeamRoster.vue:132, :140) |
| tile-announcement / danger-ink | dark | a | Both are Apple iOS 26 systemRed in dark (#FF4245; token descriptions say so). Light `danger-ink` is the darker accessible text variant, which is why they differ in light. | no: tiles reach the UI only as a `tint` background (utils/iconTile.js, GListRow); no `*-ink` token is used as a fill. |
| tile-leave / success-ink | dark | a | Both are iOS systemGreen in dark (#30D158). Light `success-ink` is the accessible variant. | no |
| tile-neutral / ink-muted | dark | a | Both are iOS systemGray (#8E8E93) in dark. Light `ink-muted` is the accessible variant. | no |
| tile-on-tile / glass-fill-fallback | light | b | `tile-on-tile` is the constant white glyph on a coloured tile and the switch thumb; the cell is white only in light. | no: used for the switch thumb (glass-components.css:3881), the tile glyph (4646) and Ionic contrast text (variables.css). No surface token is used as glyph colour. |
| tile-on-tile / ink | dark | b | Constant white vs primary text (white only in dark). | no |
| tile-on-tile / sheet-cell | light | b | Constant white vs sheet cell. | no |
| tile-on-tile / surface | light | b | Constant white vs card surface. | no |
| tile-overtime / warn-ink | dark | a | Both are iOS systemOrange (#FF9230) in dark. Light `warn-ink` is the accessible variant. | no |

Totals: 4 by design (a), 15 risk (b), 0 should split (c). 6 of the 15 risk pairs sit on
real misuse (9 sites, listed above, none fixed here); the other 9 are risk only. Minor, not
listed as misuse: `.g-lineitems` (glass-components.css:3091) is a cell inside the expense
request sheet but keeps a visible rim, so it does not disappear.

## What keeps this honest

- Do not add a pair to the baseline without adding its row here.
- `warn-fill` was split from `warn-ink` in both themes for this reason (tokens.json).
- Open question, not changed: `glass-fill` and `hair` are both rgba(255,255,255,.075) in
  dark. That is spec 2/6; splitting them is a design call, not a bug fix.
