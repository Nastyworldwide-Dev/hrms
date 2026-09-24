<template>
	<div class="flex flex-col gap-3 py-4">
		<!-- One grouped row, like every other field (alpha.6 B2): "Add a file",
		     a plain verb, instead of a dashed web drop zone under a lime heading. -->
		<label class="file-select">
			<div class="select-button cursor-pointer g-form-group">
				<div class="g-form-row">
					<span class="g-form-row__label">{{ __("Add a file") }}</span>
					<Upload class="g-form-row__switch h-5 w-5 text-ink-600" aria-hidden="true" />
				</div>
				<input
					class="hidden"
					ref="input"
					type="file"
					multiple
					accept="*"
					@change="(e) => emit('handle-file-select', e)"
				/>
			</div>
		</label>

		<div v-if="modelValue.length" class="w-full">
			<ul class="w-full flex flex-col items-center gap-2">
				<li
					class="bg-surface border border-divider p-2 w-full"
					v-for="file in modelValue"
					:key="file.file_name || file.name"
				>
					<div class="flex flex-row items-center justify-between text-inkbase text-sm">
						<span
							class="grow g-focusable"
							role="button"
							tabindex="0"
							@click="showFilePreview(file)"
							@keydown.enter.prevent="showFilePreview(file)"
							@keydown.space.prevent="showFilePreview(file)"
						>
							{{ file.file_name || file.name }}
						</span>
						<X
							class="h-4 w-4 cursor-pointer text-ink-700"
							@click="() => confirmDeleteAttachment(file)"
						/>
					</div>
				</li>
			</ul>

			<GConfirm
				:is-open="showDialog"
				:title="__('Delete attachment')"
				:confirm-label="__('Delete')"
				:cancel-label="__('Cancel')"
				destructive
				@confirm="handleFileDelete"
				@cancel="showDialog = false"
			>
				{{ __("Are you sure you want to delete the attachment") }}
				{{ selectedFile.file_name }}?
			</GConfirm>

			<!-- File Preview Modal -->
			<FilePreviewModal
				:is-open="showPreviewModal"
				:file="selectedFile"
				@did-dismiss="showPreviewModal = false"
			/>
		</div>
	</div>
</template>

<script setup>
import { Upload, X } from "lucide-vue-next"
import GConfirm from "@/components/glass/GConfirm.vue"

import { ref } from "vue"

import FilePreviewModal from "@/components/FilePreviewModal.vue"

defineProps({
	modelValue: {
		type: Object,
		required: true,
	},
})
let showDialog = ref(false)
let showPreviewModal = ref(false)
let selectedFile = ref({})

const emit = defineEmits(["handle-file-select", "handle-file-delete"])

function showFilePreview(fileObj) {
	selectedFile.value = fileObj
	showPreviewModal.value = true
}

function confirmDeleteAttachment(fileObj) {
	selectedFile.value = fileObj
	showDialog.value = true
}

function handleFileDelete() {
	emit("handle-file-delete", selectedFile.value)
	showDialog.value = false
}
</script>
