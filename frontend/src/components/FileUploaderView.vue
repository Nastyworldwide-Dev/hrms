<template>
	<!-- Nothing to add and nothing attached: no empty band (alpha.14). -->
	<div v-if="!readOnly || modelValue.length" class="flex flex-col gap-3 py-4">
		<!-- One grouped row, like every other field (alpha.6 B2): "Add a file",
		     a plain verb, instead of a dashed web drop zone under a lime heading. -->
		<!-- A decided request's files are shown, not changed (alpha.14 G). -->
		<label v-if="!readOnly" class="file-select">
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
			<GAttachmentRow
				v-for="file in modelValue"
				:key="file.file_name || file.name"
				:file="file"
				:removable="!readOnly"
				@open="showFilePreview"
				@remove="confirmDeleteAttachment"
			/>

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
import { Upload } from "lucide-vue-next"
import GConfirm from "@/components/glass/GConfirm.vue"
import GAttachmentRow from "@/components/glass/GAttachmentRow.vue"

import { ref } from "vue"

import FilePreviewModal from "@/components/FilePreviewModal.vue"

defineProps({
	modelValue: {
		type: Object,
		required: true,
	},
	readOnly: { type: Boolean, default: false },
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
