GOAL: pages stop at their edges; no refresh words on a light pull; bell = avatar; tab icon centred in its pill
DONE WHEN: WebKit: forceOverscroll false on every ion-content; bell 44x44 = avatar 44x44; tab gap 7/7 (was 0/14); ios gate 0/0/0/0
CHECK: node --test frontend/src/components/__tests__/alpha10-frame.test.js; node design/gates/ios.mjs
