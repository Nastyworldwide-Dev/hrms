# HANDOFF
prompt:   alpha.7 (go till finish)
status:   done
commit:   68869d581 on nz-glass (tag v2.0.0-alpha.7)
files:    frontend/src/theme/glass-components.css
          frontend/src/views/Home.vue
          frontend/src/components/MustReadNotice.vue
          hrms/api/announcements.py
          hrms/hr/doctype/hr_announcement/hr_announcement.json
          hrms/hr/report/announcement_confirmations/
          hrms/patches/v16_0/announcement_alpha7_fields.py
          docs/glass/CHANGELOG.md
verify:   deploy nz-glass; open Nadi on iPhone Safari; Desk > HR Announcement > Preview as staff
flags:    moved to alpha.8: Dynamic Type, Search (needs who-finds-whom ruling), spring motion; offline check-in never (owner rule)
next:     owner deploys; answer the Search ruling before alpha.8
