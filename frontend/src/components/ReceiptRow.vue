<!--
  The receipt on one expense line (owner, 20 Oct 2026, alpha.60 #2): one row,
  "Add a file", in the item sheet. It replaces the one file asked for at the
  bottom of the whole claim.

  Shaped on TimeSlipFields' file row (same classes, same a11y), with one
  difference: this file is sent the moment it is picked, with no parent (the
  claim does not exist yet), and the line keeps only its URL. The server checks
  the file is the claim owner's and files it under the claim when the claim is
  saved (ExpenseClaim.link_receipts).

  Props:
    url       string  — the line's receipt (a file URL), "" for none
    required  boolean — the line's type needs a receipt: the row says "Required"
    readOnly  boolean — a sent claim: the receipt is shown as a tap-to-open file
  Emits: update:url (the uploaded file's URL), update:uploading (true while sending)
-->
<template>
	<div v-if="!readOnly || url" :class="{ 'g-form-group': !readOnly }">
		<label v-if="!readOnly" class="g-form-row receipt-file">
			<span class="g-form-row__label">{{ __("Add a file") }}</span>
			<!-- A picked file: its name, and that a tap replaces it. While it is
			     sent the row says so; the input's own label says the same to a
			     screen reader, since an aria-label replaces the row's text. -->
			<span class="receipt-file__name" :class="{ 'is-empty': !url || uploading }">
				<template v-if="uploading">{{ __("Uploading…") }}</template>
				<template v-else-if="url">{{ name }}</template>
				<template v-else-if="required">{{ __("Required") }}</template>
				<span v-if="url && !uploading" class="receipt-file__hint">{{ __("Tap to replace") }}</span>
			</span>
			<Check
				v-if="url && !uploading"
				class="g-form-row__switch h-5 w-5 receipt-file__tick"
				aria-hidden="true"
			/>
			<Upload v-else class="g-form-row__switch h-5 w-5 text-ink-600" aria-hidden="true" />
			<!-- g-sr, not display:none: a keyboard or screen reader reaches the
			     proof (design review of c9a824c15), as TimeSlipFields does -->
			<input
				class="g-sr"
				type="file"
				:accept="SLIP_FILE_TYPES"
				:disabled="uploading"
				:aria-label="label"
				@change="pick"
			/>
		</label>
		<!-- A decided claim's receipt is shown, not changed: a tap opens it -->
		<template v-else>
			<GAttachmentRow :file="file" @open="preview = true" />
			<FilePreviewModal :is-open="preview" :file="file" @did-dismiss="preview = false" />
		</template>
	</div>
</template>

<script setup>
import { Check, Upload } from "lucide-vue-next"
import { computed, inject, onBeforeUnmount, ref } from "vue"

import FilePreviewModal from "@/components/FilePreviewModal.vue"
import GAttachmentRow from "@/components/glass/GAttachmentRow.vue"
import { FileAttachment } from "@/composables"
import { receiptName } from "@/utils/receiptName"
// the types the server's upload takes (hrms.api.upload_base64_file): the same list a time slip offers
import { SLIP_FILE_TYPES } from "@/utils/timeSlip"

const props = defineProps({
	url: { type: String, default: "" },
	required: { type: Boolean, default: false },
	readOnly: { type: Boolean, default: false },
})
const emit = defineEmits(["update:url", "update:uploading"])

const __ = inject("$translate")
const uploading = ref(false)
const preview = ref(false)
// the sheet can close mid-upload; a late answer must not land in the next item
let alive = true
onBeforeUnmount(() => (alive = false))

const name = computed(() => receiptName(props.url))
// the shape GAttachmentRow and FilePreviewModal read; one object, not one per render
const file = computed(() => ({ file_name: name.value, file_url: props.url }))
const label = computed(() => {
	if (uploading.value) return __("Add a file, uploading")
	if (props.url) return __("Add a file, {0}. Tap to replace", [name.value])
	return props.required ? __("Add a file, required") : __("Add a file")
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
		console.info("[ReceiptRow] receipt uploaded", uploaded.file_name)
		emit("update:url", uploaded.file_url)
	} catch (error) {
		// FileAttachment already told the person why; the old receipt stays
		console.warn("[ReceiptRow] receipt upload failed; keeping the old file", error?.exc_type || "")
	} finally {
		// the same file can be picked again after a failure
		input.value = ""
		if (alive) uploading.value = false
		emit("update:uploading", false)
	}
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
/* name above, the hint under it: the row grows rather than truncating the hint */
.receipt-file__hint {
	display: block;
	white-space: normal;
	font-size: var(--g-type-caption-size);
	color: var(--g-ink2);
}
.receipt-file__tick {
	color: var(--g-success-ink);
}
.receipt-file__name.is-empty {
	color: var(--g-ink2);
}
</style>
