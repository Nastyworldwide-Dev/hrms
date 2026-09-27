<!--
  GAttachmentRow — one attached file, shown as what it is (alpha.14; owner,
  27 Sep 2026: "every attachment must show preview"). An image shows itself
  as a 44 pt thumbnail; a PDF or any other file a typed mark. The name
  trails in the row; a tap opens the full preview. Optional remove.

  Props:
    file       object — a Frappe File row ({ file_name, file_url }) or a picked
               browser File (not uploaded yet)
    removable  boolean — shows a 44 pt remove button
  Emits: open, remove
-->
<template>
	<div class="g-attachment">
		<button type="button" class="g-attachment__open g-focusable" @click="$emit('open', file)">
			<img v-if="kind === 'image' && src" :src="src" alt="" class="g-attachment__thumb" loading="lazy" />
			<span v-else class="g-attachment__thumb g-attachment__thumb--mark" aria-hidden="true">
				{{ kind === "pdf" ? "PDF" : extension }}
			</span>
			<span class="g-attachment__name">{{ name }}</span>
		</button>
		<button
			v-if="removable"
			type="button"
			class="g-attachment__remove g-focusable"
			:aria-label="__('Remove {0}', [name])"
			@click="$emit('remove', file)"
		>
			<svg class="g-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
				<path d="M4 4l8 8M12 4l-8 8" />
			</svg>
		</button>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount } from "vue"
import { attachmentKind } from "@/utils/attachmentKind"

const __ = inject("$translate", (s, a) => (a ? s.replace(/\{(\d)\}/g, (_m, n) => a[n]) : s))
const props = defineProps({
	file: { type: Object, required: true },
	removable: { type: Boolean, default: false },
})
defineEmits(["open", "remove"])

const name = computed(() => props.file.file_name || props.file.name || "")
const kind = computed(() => attachmentKind(props.file))
const extension = computed(() => (name.value.match(/\.([a-z0-9]{1,4})$/i)?.[1] || "File").toUpperCase())
// a picked file has no URL yet: an object URL, released when the row goes
const objectUrl = !props.file.file_url && props.file instanceof Blob ? URL.createObjectURL(props.file) : ""
const src = computed(() => props.file.file_url || objectUrl)
onBeforeUnmount(() => objectUrl && URL.revokeObjectURL(objectUrl))
</script>
