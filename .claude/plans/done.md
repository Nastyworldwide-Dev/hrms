GOAL: the gates measure Nadi as installed on an iPhone (safe areas, standalone) and walk it like a person, tab to tab.
DONE WHEN: device-journey-audit runs in the ios gate; it went red on HEAD for real defects (double title after Back, 21 pt top band).
CHECK: node --test frontend/e2e/device.test.mjs; cd frontend && node e2e/device-journey-audit.mjs
