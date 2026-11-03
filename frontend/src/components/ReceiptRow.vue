<!--
  The receipts on one expense line (owner, 20 Oct 2026, alpha.60 #2; several per
  line since 3 Nov 2026). One "Add a file" row in the item sheet, and every file
  added listed under it. It replaces the one file asked for at the bottom of the
  whole claim.

  Each file is sent the moment it is picked, with no parent (the claim does not
  exist yet), and the line keeps only URLs: the first in `receipt` (every older
  reader keeps working), the rest in `more_receipts`, one per line
  (utils/lineReceipts.js). The server checks each file is the claim owner's and
  files it under the claim when the claim is saved (ExpenseClaim.link_receipts).

  Props:
    url       string  — the line's first receipt (a file URL), "" for none
    more      string  — the line's other receipts, one URL per line
    required  boolean — the line's type needs a receipt: the row says "Required"
    readOnly  boolean — a sent claim: the receipts are shown as tap-to-open files
  Emits: update:url, update:more (the line's two fields), update:uploading (true while sending)
-->
<template>
	<div v-if="!readOnly || files.length" :class="{ 'g-form-group': !readOnly }">
		<label v-if="!readOnly" class="g-form-row receipt-file">
			<span class="g-form-row__label">{{ __("Add a file") }}</span>
			<!-- While a file is sent the row says so; the input's own label says the
			     same to a screen reader, since an aria-label replaces the row's text. -->
			<span class="receipt-file__name" :class="{ 'is-empty': !files.length || uploading }">
				<template v-if="uploading">{{ __("Uploading…") }}</template>
				<template v-else-if="files.length">{{ __("Add another") }}</template>
				<template v-else-if="required">{{ __("Required") }}</template>
			</span>
			<Upload class="g-form-row__switch h-5 w-5 text-ink-600" aria-hidden="true" />
			<!-- g-sr, not display:none: a keyboard or screen reader reaches the
			     proof (design review of c9a824c15), as TimeSlipFields does -->
			<input
				class="g-sr"
				type="file"
				multiple
				:accept="SLIP_FILE_TYPES"
				:disabled="uploading"
				:aria-label="label"
				@change="pick"
			/>
		</label>
		<!-- every file on the line: a tap opens it; before sending, each can be taken off -->
		<GAttachmentRow
			v-for="file in files"
			:key="file.file_url"
			:file="file"
			:removable="!readOnly"
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
import { Upload } from "lucide-vue-next"
import { computed, inject, onBeforeUnmount, ref } from "vue"

import FilePreviewModal from "@/components/FilePreviewModal.vue"
import GAttachmentRow from "@/components/glass/GAttachmentRow.vue"
import { FileAttachment } from "@/composables"
import { fromReceiptList, toReceiptList } from "@/utils/lineReceipts"
import { receiptName } from "@/utils/receiptName"
// the types the server's upload takes (hrms.api.upload_base64_file): the same list a time slip offers
import { SLIP_FILE_TYPES } from "@/utils/timeSlip"

const props = defineProps({
	url: { type: String, default: "" },
	more: { type: String, default: "" },
	required: { type: Boolean, default: false },
	readOnly: { type: Boolean, default: false },
})
const emit = defineEmits(["update:url", "update:more", "update:uploading"])

const __ = inject("$translate")
const uploading = ref(false)
const preview = ref(null)
// the sheet can close mid-upload; a late answer must not land in the next item
let alive = true
onBeforeUnmount(() => (alive = false))

const urls = computed(() => toReceiptList(props.url, props.more))
// the shape GAttachmentRow and FilePreviewModal read
const files = computed(() =>
	urls.value.map((url) => ({ file_name: receiptName(url), file_url: url }))
)
const label = computed(() => {
	if (uploading.value) return __("Add a file, uploading")
	if (files.value.length) return __("Add a file, {0} added. Add another", [files.value.length])
	return props.required ? __("Add a file, required") : __("Add a file")
})

function save(list) {
	const { receipt, more_receipts } = fromReceiptList(list)
	emit("update:url", receipt)
	emit("update:more", more_receipts)
}

async function pick(event) {
	const input = event.target
	const picked = [...(input.files || [])]
	if (!picked.length) return
	uploading.value = true
	emit("update:uploading", true)
	let list = urls.value
	try {
		// one at a time, in the order picked: each upload already toasts its own failure
		for (const file of picked) {
			try {
				const uploaded = await new FileAttachment(file).upload(null, null, "")
				if (!alive) return
				list = toReceiptList(list.join("\n"), uploaded.file_url)
			} catch (error) {
				// FileAttachment already told the person why; the files so far stay
				console.warn(
					"[ReceiptRow] one receipt failed to upload; keeping the others",
					error?.exc_type || ""
				)
			}
		}
		console.info("[ReceiptRow] receipts on the line:", list.length)
		save(list)
	} finally {
		// the same file can be picked again after a failure
		input.value = ""
		if (alive) uploading.value = false
		emit("update:uploading", false)
	}
}

function remove(file) {
	console.info("[ReceiptRow] receipt taken off the line", file.file_name)
	save(urls.value.filter((url) => url !== file.file_url))
}
</script>

<style>
.receipt-file {
	/* the visually hidden input is positioned against its own row, so focusing it
	   never scrolls the page elsewhere (design review of 364233f86) */
	position: relative;
	cursor: pointer;
}
/* the hidden input takes the focus; the row shows it, as .g-focusable does */
.receipt-file:has(input:focus-visible) {
	box-shadow: var(--g-shadow-focus-ring);
}
.receipt-file__name {
	flex: 1 1 auto;
	min-width: 0;
	overflow: hidden;
	text-align: end;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--g-ink);
}
.receipt-file__name.is-empty {
	color: var(--g-ink2);
}
</style>
