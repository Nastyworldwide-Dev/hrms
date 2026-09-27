GOAL: the first screen downloads less code: unused Ionic wrappers dropped, Tailwind CSS only for components the app renders.
DONE WHEN: FCP on the alpha.12 slow-phone profile drops (5.68 -> 5.28 s); main JS 492 -> 467 KB; CSS 182 -> 150 KB; no screen's computed styles change.
CHECK: node frontend/e2e/first-paint.mjs; per-element computed-style diff old vs new CSS on 36 screens (only class order on 2); device journey 0; page-audit 0; yarn test green
