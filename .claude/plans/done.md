GOAL: scrolling inside a sheet scrolls its content and never moves or closes the sheet.
DONE WHEN: GModal's content scrolls inside an ion-content (the only element Ionic 7's sheet gesture yields to); the head stays outside it.
CHECK: yarn --cwd frontend test (1549); live phone probe on fresh.local — day sheet: before, a drag down after scrolling moved the sheet 100 px; after, the list scrolls (250 -> 18) and the sheet stays at 80. Holidays: before, a gentle drag closed it; after, it stays open. iOS gate: 9/9 audits, 0 findings.
