<template>
	<div class="flex flex-col gap-3 py-4">
		<label class="file-select">
			<h2 class="g-eyebrow pb-4">{{ __("Attachments") }}</h2>
			<div class="select-button cursor-pointer">
				<div
					class="flex flex-col w-full bg-surface border border-divider rounded-input items-center p-4 gap-2"
				>
					<FeatherIcon name="upload" class="h-6 w-6 text-ink-700" />
					<span class="block text-sm font-normal leading-5 text-ink-700">
						{{ __("Upload images or documents") }}
					</span>
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
						<span class="grow" @click="showFilePreview(file)">
							{{ file.file_name || file.name }}
						</span>
						<FeatherIcon
							name="x"
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
			<ion-modal ref="modal" :is-open="showPreviewModal" @didDismiss="showPreviewModal = false">
				<FilePreviewModal :file="selectedFile" />
			</ion-modal>
		</div>
	</div>
</template>

<script setup>
import GConfirm from "@/components/glass/GConfirm.vue"
import { FeatherIcon } from "frappe-ui"
import { ref } from "vue"
import { IonModal } from "@ionic/vue"

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

<style scoped>
ion-modal {
	--height: 100%;
}
</style>
