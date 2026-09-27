GOAL: every attached file shows what it is (image thumbnail, PDF/type mark) and opens a preview; a file picked on the IT ticket form is kept and uploaded.
DONE WHEN: FileUploaderView, RequestActionSheet and GFileUpload all render GAttachmentRow; TicketNew handles select/preview/remove.
CHECK: node --test frontend/src/utils/__tests__/attachmentKind.test.js; leave form WebKit: PDF mark + image thumbnail; page-audit 402 + sheet audit 0
