CLASS: an attachment shown as its file name only (no preview); and a picked file lost because the parent never handled the picker's event
frontend/src/components/FileUploaderView.vue:22 same-root — every request form's files
frontend/src/components/RequestActionSheet.vue:56 same-root — a request's files in its sheet
frontend/src/components/glass/GFileUpload.vue:42 same-root — ticket picker rows
frontend/src/views/helpdesk/TicketNew.vue:86 same-root — v-model only: picks never reached files (GFileUpload emits select, not update:modelValue)
frontend/src/views/sop/SopDetail.vue:46 not-affected — already previews image and PDF inline
frontend/src/components/CheckinSheet.vue:17 not-affected — shows the photo itself (27e4f4c9a)
