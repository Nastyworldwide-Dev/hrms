GOAL: The glass panel's decorative gloss stops fading the text under it.
DONE WHEN: .g-glass::after carries z-index -1, .g-glass isolates, and no
 full-bleed pseudo-overlay in the stylesheet paints above its own content.
CHECK: cd frontend && node --experimental-test-module-mocks --test
 src/theme/__tests__/glass-sheen-paints-below-content.test.js
