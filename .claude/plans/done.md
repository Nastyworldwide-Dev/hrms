GOAL: a lighter first download: code only one screen or a later moment needs loads when it is needed
DONE WHEN: main JS 570 -> 490 KB; slow-phone first paint 6.3 -> ~5.4 s; push still starts; no page errors; tests green
CHECK: cd frontend && node --test src/components/__tests__/no-ionic-overlays.test.js src/utils/__tests__/frappe-push-notification.test.js
