<!-- A file preview, as a sheet titled with the file's name (the sheet's own
     bar carries the Close X; the old ion-toolbar had a text "Close"). -->
<template>
	<GModal :is-open="isOpen" :title="filename" @did-dismiss="$emit('did-dismiss')">
		<div v-if="isOpen && src" class="file-preview w-full overflow-auto touch-pinch-zoom">
			<template v-if="isImageFile">
				<!-- A long image (a phone screenshot) opens cropped to its top, with a fade
				     and "Show whole image" (owner, 13 Nov 2026); tapping it does the same. -->
				<button
					v-if="cropped"
					type="button"
					class="file-preview__crop"
					:aria-label="__('Show whole image')"
					@click="showWhole"
				>
					<img :src="src" :alt="filename" class="h-auto w-full image-preview" @load="measure" />
					<span class="file-preview__fade" aria-hidden="true"></span>
				</button>
				<img
					v-else
					:src="src"
					:alt="filename"
					class="h-auto w-full image-preview"
					@load="measure"
				/>
				<div v-if="isLong" class="file-preview__toggle">
					<GGhostButton
						:label="cropped ? __('Show whole image') : __('Show less')"
						@click="cropped ? showWhole() : (expanded = false)"
					/>
				</div>
			</template>
			<iframe v-else :src="src" :title="filename" class="w-full h-full"></iframe>
		</div>
	</GModal>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, shallowRef, watch } from "vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GModal from "@/components/glass/GModal.vue"

import { isLongImage } from "@/utils/previewCrop"
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
//: The image's own shape, read once it loads, and whether the person asked for all of it.
const isLong = ref(false)
const expanded = ref(false)
watch(
	() => props.file,
	(file) => {
		preview.value.release()
		preview.value = previewSource(file)
		isLong.value = false
		expanded.value = false
	},
	{ immediate: true }
)
const src = computed(() => preview.value.src)
const cropped = computed(() => isLong.value && !expanded.value)

const isImageFile = computed(() => {
	return /\.(gif|jpg|jpeg|tiff|png|svg|webp)$/i.test(filename.value)
})

function measure(event) {
	const img = event.target
	isLong.value = isLongImage(img.naturalWidth, img.naturalHeight)
}

function showWhole() {
	expanded.value = true
	console.info("[FilePreviewModal] showing the whole image:", filename.value)
}

onBeforeUnmount(() => preview.value.release())
</script>

<style scoped>
.image-preview {
	image-orientation: from-image;
	display: block;
}
/* a document needs room: the iframe has no height of its own. The sheet's
   own ceiling (the one place dvh is allowed), less its bar. */
.file-preview {
	height: calc(var(--g-sheet-max-height) - 6rem);
}
/* the cropped view: the top of a long image, as tall as it is wide */
.file-preview__crop {
	position: relative;
	display: block;
	width: 100%;
	aspect-ratio: 1 / 1;
	max-height: calc(var(--g-sheet-max-height) - 11rem);
	overflow: hidden;
	padding: 0;
	border: 0;
	background: none;
	cursor: zoom-in;
	border-radius: var(--g-radius-well, 8px);
}
.file-preview__fade {
	position: absolute;
	inset: auto 0 0 0;
	height: 30%;
	background: linear-gradient(to bottom, transparent, var(--g-sheet-bg, var(--g-bg)));
	pointer-events: none;
}
.file-preview__toggle {
	display: flex;
	justify-content: center;
	padding: 12px 0 4px;
}
</style>
