GOAL: your own check-in opens as a plain sheet: "In · 8:58 am", the day, the photo itself, where in words; coordinates kept but quiet (tap to copy).
DONE WHEN: Check-ins opens CheckinSheet (not the generic request sheet with raw Latitude/Longitude rows); photo loads through the private route; strangers get 403.
CHECK: node --test frontend/src/utils/__tests__/checkinSheet.test.js; WebKit screenshot with a ZZAUDIT punch (photo 480px loaded); stranger 403, guest 403
