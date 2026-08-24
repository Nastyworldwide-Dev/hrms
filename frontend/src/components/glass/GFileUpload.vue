<!--
  GFileUpload — attachment list and picker (spec §10.3 treatment list).
  Ports the behaviour of FileUploaderView.vue: a list of attachments, each
  opening a preview on tap and removable via a trailing control, with delete
  confirmed rather than immediate. FileUploaderView.vue is NOT modified.

  Not a glass surface — it sits inside a form panel, and glass inside glass
  would nest (§15).

  Confirmation is emitted, not owned: `remove` fires only after the caller
  confirms, so the existing Dialog-based confirm keeps working through the
  phase 5 swap rather than being replaced by a second confirm mechanism.

  Props:
    modelValue  array, required — [{ name, file_name }] as Frappe returns
    uploading   boolean — §11.2 skeleton row while a file is in flight
    label       string, default "Attachments"
    accept      string — passthrough to the file input
  Emits:
    preview(file)  — a file name was tapped
    remove(file)   — the remove control was used; caller confirms then updates
    select(files)  — files chosen from the picker (FileList)
  Slot: empty — §11.1 empty state when there are no attachments
-->
<template>
	<div class="g-files">
		<label class="g-file__drop g-focusable">
			<input
				type="file"
				class="g-sr"
				multiple
				:accept="accept"
				@change="$emit('select', $event.target.files)"
			/>
			{{ label }}
		</label>

		<div v-if="uploading" class="g-file" aria-hidden="true">
			<GSkeleton width="62%" height="11px" />
		</div>

		<div v-for="file in modelValue" :key="file.file_name || file.name" class="g-file">
			<button type="button" class="g-file__name g-focusable" @click="$emit('preview', file)">
				{{ file.file_name || file.name }}
			</button>
			<button
				type="button"
				class="g-file__remove g-focusable"
				:aria-label="`Remove ${file.file_name || file.name}`"
				@click="$emit('remove', file)"
			>
				<svg class="g-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
					<path d="M4 4l8 8M12 4l-8 8" />
				</svg>
			</button>
		</div>

		<slot v-if="!modelValue.length && !uploading" name="empty" />
	</div>
</template>

<script setup>
import GSkeleton from "./GSkeleton.vue"

defineProps({
	modelValue: { type: Array, default: () => [] },
	uploading: { type: Boolean, default: false },
	label: { type: String, default: "Attachments" },
	accept: { type: String, default: "" },
})
defineEmits(["preview", "remove", "select"])
</script>
