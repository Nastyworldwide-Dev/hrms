GOAL: closing any sheet that holds a file preview no longer throws.
DONE WHEN: FilePreviewModal makes a blob URL only for a real Blob, once, and releases it once (utils/previewSource.js).
CHECK: node --test frontend/src/components/__tests__/file-preview-no-crash.test.js; live: opening/closing Your request and Time off requests 3x each — before, TypeError "createObjectURL ... Overload resolution failed" per close; after, none; a picked PNG still previews (blob:, naturalWidth 1).
