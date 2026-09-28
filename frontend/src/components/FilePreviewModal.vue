<!-- A file preview, as a sheet titled with the file's name (the sheet's own
     bar carries the Close X; the old ion-toolbar had a text "Close"). -->
<template>
	<GModal :is-open="isOpen" :title="filename" @did-dismiss="$emit('did-dismiss')">
		<div v-if="isOpen && src" class="file-preview w-full overflow-auto touch-pinch-zoom">
			<img v-if="isImageFile" :src="src" :alt="filename" class="h-auto w-full image-preview" />
			<iframe v-else :src="src" :title="filename" class="w-full h-full"></iframe>
		</div>
	</GModal>
</template>

<script setup>
import { computed, onBeforeUnmount, shallowRef, watch } from "vue"
import GModal from "@/components/glass/GModal.vue"

import { previewSource } from "@/utils/previewSource"

const props = defineProps({
	isOpen: {
		type: Boolean,
		default: false,
	},
	file: {
		type: Object,
		default: null,
	},
})
defineEmits(["did-dismiss"])

const filename = computed(() => {
	return props.file?.file_name || props.file?.name || ""
})

//: One source per file, made when the file changes and released when it
//: changes again or the preview goes away (utils/previewSource.js). Callers
//: start with `file = {}`, and a computed that called URL.createObjectURL on
//: it threw on every close of the request sheet (crash hunt, 28 Sep 2026).
const preview = shallowRef(previewSource(null))
watch(
	() => props.file,
	(file) => {
		preview.value.release()
		preview.value = previewSource(file)
	},
	{ immediate: true }
)
const src = computed(() => preview.value.src)

const isImageFile = computed(() => {
	return /\.(gif|jpg|jpeg|tiff|png|svg)$/i.test(filename.value)
})

onBeforeUnmount(() => preview.value.release())
</script>

<style scoped>
.image-preview {
	image-orientation: from-image;
}
/* a document needs room: the iframe has no height of its own. The sheet's
   own ceiling (the one place dvh is allowed), less its bar. */
.file-preview {
	height: calc(var(--g-sheet-max-height) - 6rem);
}
</style>
