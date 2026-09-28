CLASS: URL.createObjectURL called on something that is not a Blob (a caller's `{}` placeholder)
frontend/src/components/FilePreviewModal.vue same-root — source now from previewSource(); the only caller of createObjectURL on a prop that may be {}
frontend/src/components/glass/GAttachmentRow.vue:51 not-affected — already guards `props.file instanceof Blob`
frontend/src/components/RequestActionSheet.vue:282 not-affected — passes the `{}` placeholder; the modal now handles it
frontend/src/components/FileUploaderView.vue:75 not-affected — same placeholder, same handling
