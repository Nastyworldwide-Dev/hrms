# HANDOFF
prompt:   28 Sep 2026 — calendar team, OT report columns, TruTrip, update bar
status:   done
commit:   7b48b8fa5 on nz-glass (tag v2.0.0-alpha.15)
files:    hrms/api/calendar.py
          hrms/api/team.py
          frontend/src/components/DaySheet.vue
          hrms/hr/doctype/ot_request/ot_request.json
          hrms/patches/v16_0/ot_request_approved_on_and_payment.py
          frontend/src/views/More.vue
          frontend/src/components/UpdatePrompt.vue
          frontend/public/sw.js
verify:   bench --site <site> migrate; then open Calendar as a senior, and OT Request report as HR
flags:    6621d7bd9 carries b2f020a62's subject by mistake (diff is a vite.config.js comment only)
next:     deploy on Frappe Cloud; migrate runs the OT patch (fills Approved On, Payment=Pending)
