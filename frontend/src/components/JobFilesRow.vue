<!--
  Optional files with the draft job description on a Manpower Request (owner,
  29 Oct 2026: "requester can put attachment there and it is not required").
  Any number. Each file is sent the moment it is picked, with no parent (the
  request does not exist yet); the request keeps their URLs, and the server
  files them under the request when it is sent (link_job_files), so whoever can
  open the request can open them.

  Shaped on ReceiptRow (same row, same hidden input, same a11y).

  Props:
    files  array — [{ file_url, file_name }] already added
  Emits: update:files (the new list), update:uploading (true while sending),
         uploaded (the File just sent; the wizard reads a JD's text from it)
-->
<template>
	<div class="g-form-group">
		<label class="g-form-row receipt-file">
			<span class="g-form-row__label">{{ __("Attachments (optional)") }}</span>
			<span class="g-form-row__value">
				<template v-if="uploading">{{ __("Uploading…") }}</template>
				<template v-else>{{ files.length ? __("Add another") : __("Add a file") }}</template>
			</span>
			<input
				type="file"
				class="sr-only"
				:accept="JOB_FILE_TYPES"
				:disabled="uploading"
				:aria-label="label"
				@change="pick"
			/>
		</label>
		<GAttachmentRow
			v-for="file in files"
			:key="file.file_url"
			:file="file"
			removable
			@open="preview = file"
			@remove="remove(file)"
		/>
		<FilePreviewModal
			:is-open="Boolean(preview)"
			:file="preview || {}"
			@did-dismiss="preview = null"
		/>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref } from "vue"

import FilePreviewModal from "@/components/FilePreviewModal.vue"
import GAttachmentRow from "@/components/glass/GAttachmentRow.vue"
import { FileAttachment } from "@/composables"
import { JOB_FILE_TYPES, withFile, withoutFile } from "@/utils/jobFiles"

const props = defineProps({
	files: { type: Array, default: () => [] },
})
const emit = defineEmits(["update:files", "update:uploading", "uploaded"])

const __ = inject("$translate")
const uploading = ref(false)
const preview = ref(null)
// the page can be left mid-upload; a late answer must not land anywhere
let alive = true
onBeforeUnmount(() => (alive = false))

const label = computed(() => {
	if (uploading.value) return __("Attachments, uploading")
	return props.files.length
		? __("Attachments, {0} added. Add another", [props.files.length])
		: __("Attachments, optional. Add a file")
})

async function pick(event) {
	const input = event.target
	const picked = input.files?.[0]
	if (!picked) return
	uploading.value = true
	emit("update:uploading", true)
	try {
		const uploaded = await new FileAttachment(picked).upload(null, null, "")
		if (!alive) return
		console.info("[JobFilesRow] file uploaded", uploaded.file_name)
		emit("update:files", withFile(props.files, uploaded))
		// the wizard may fill the job description from it
		emit("uploaded", uploaded)
	} catch (error) {
		// FileAttachment already told the person why; the list stays as it was
		console.warn("[JobFilesRow] upload failed", error?.exc_type || "")
	} finally {
		// the same file can be picked again after a failure
		input.value = ""
		if (alive) uploading.value = false
		emit("update:uploading", false)
	}
}

function remove(file) {
	console.info("[JobFilesRow] file removed", file.file_name)
	emit("update:files", withoutFile(props.files, file))
}
</script>
