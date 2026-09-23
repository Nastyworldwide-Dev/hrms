<!-- A file preview, as a sheet titled with the file's name (the sheet's own
     bar carries the Close X; the old ion-toolbar had a text "Close"). -->
<template>
	<GModal :is-open="isOpen" :title="filename" @did-dismiss="$emit('did-dismiss')">
		<div v-if="isOpen && file" class="file-preview w-full overflow-auto touch-pinch-zoom">
			<img v-if="isImageFile" :src="src" :alt="filename" class="h-auto w-full image-preview" />
			<iframe v-else :src="src" :title="filename" class="w-full h-full"></iframe>
		</div>
	</GModal>
</template>

<script setup>
import { computed, onBeforeUnmount } from "vue"
import GModal from "@/components/glass/GModal.vue"

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

const src = computed(() => {
	return props.file.file_url ? props.file.file_url : URL.createObjectURL(props.file)
})

const isImageFile = computed(() => {
	return /\.(gif|jpg|jpeg|tiff|png|svg)$/i.test(filename.value)
})

onBeforeUnmount(() => {
	if (props.file && !props.file.file_url) URL.revokeObjectURL(src.value)
})
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
