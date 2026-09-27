GOAL: a row's value sits at its trailing edge beside the chevron; icons in a row keep their own size.
DONE WHEN: the shared row fill rule skips svg; check-in row time ends at the chevron (x 342, chevron 354-370).
CHECK: node --test frontend/src/theme/__tests__/row-accessory.test.js; page-audit 402 GATE_COUNT 0
