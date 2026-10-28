CLASS: (a) a GET-only endpoint called with frappe-ui's default POST; (b) a translated string using %s, which __ never fills
frontend/src/views/OrgChart.vue same-root — get_node resource is GET; %s -> {0}
frontend/src/utils/orgChart.js same-root — %s -> {0}/{1}
frontend/src/views/attendance/AttendanceDownload.vue not-affected — already method GET (the class test scans every GET endpoint caller and found no other)
