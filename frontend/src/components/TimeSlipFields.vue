<!--
  The two rows a time slip asks for: why, and the proof (owner, 14 Oct 2026).

  Shared by the check-in sheet (before the punch) and Today (after it), so the
  two ask in the same words. The file is held by the caller (v-model:file) and
  sent by utils/timeSlip.js; this only picks it. "Required" is said on the row
  before Send, not only refused at it (as FileUploaderView does).
-->
<template>
	<div class="g-form-group">
		<div class="g-form-row">
			<span class="g-form-row__label">{{ __("Reason") }}</span>
			<GSelect :model-value="TIME_SLIP_REASON" :options="reasons" :aria-label="__('Reason')" />
		</div>
		<label class="g-form-row timeslip-file">
			<span class="g-form-row__label">{{ __("Add a file") }}</span>
			<span class="timeslip-file__name" :class="{ 'is-empty': !file }">
				{{ file ? file.name : __("Required") }}
			</span>
			<Upload class="g-form-row__switch h-5 w-5 text-ink-600" aria-hidden="true" />
			<!-- g-sr, not display:none: a keyboard or screen reader reaches the
			     required proof (design review of c9a824c15), as GFileUpload does -->
			<input
				class="g-sr"
				type="file"
				:accept="SLIP_FILE_TYPES"
				:aria-label="__('Add a file')"
				@change="pick"
			/>
		</label>
	</div>
</template>

<script setup>
import { Upload } from "lucide-vue-next"
import { computed, inject } from "vue"

import GSelect from "@/components/glass/GSelect.vue"
import { SLIP_FILE_TYPES, TIME_SLIP_REASON } from "@/utils/timeSlip"

defineProps({ file: { type: Object, default: null } })
const emit = defineEmits(["update:file"])

const __ = inject("$translate")
// one reason today; the server holds the list
const reasons = computed(() => [{ label: __("Clinic visit"), value: TIME_SLIP_REASON }])

function pick(event) {
	emit("update:file", event.target.files?.[0] ?? null)
}
</script>

<style>
.timeslip-file {
	/* the visually hidden input is positioned against its own row, so focusing it
	   never scrolls the page elsewhere (design review of 364233f86) */
	position: relative;
	cursor: pointer;
}
/* the hidden input takes the focus; the row shows it, as .g-focusable does */
.timeslip-file:has(input:focus-visible) {
	box-shadow: var(--g-shadow-focus-ring);
}
.timeslip-file__name {
	overflow: hidden;
	text-align: end;
	text-overflow: ellipsis;
	white-space: nowrap;
	color: var(--g-ink);
}
.timeslip-file__name.is-empty {
	color: var(--g-ink2);
}
</style>
