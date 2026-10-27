CLASS: a Confirm button shown where the server refuses the confirmation (dead button)
hrms/api/announcements.py get_announcement same-root — payload says live
frontend/src/views/announcements/Detail.vue same-root — tick + Confirm only when live
frontend/src/components/MustReadNotice.vue not-affected — fed by must_read (live notices only)
