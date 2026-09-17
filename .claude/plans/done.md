GOAL: No surface asserts a distance, in numbers or in words, that a coarse
 reading cannot support — and none of them re-derives what "coarse" means.
DONE WHEN: title, subtitle and headline all ask isReadingCoarse; the shared
 helper is exported once and no surface compares against the cap itself; the
 dialog reads the accuracy the SERVER judged on, echoed by the punch.
CHECK: cd frontend && node --experimental-test-module-mocks --test
 src/components/__tests__/geofence-dialogs-do-not-overclaim.test.js
