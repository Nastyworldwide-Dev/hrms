<template>
	<!-- Manage folders (owner, 27 Oct 2026; mockup state 7): HR reorders,
	     renames, and deletes an empty folder. Each change reloads the list. -->
	<GModal :is-open="props.open" :title="__('Manage folders')" @did-dismiss="close">
		<div class="g-form-body">
			<section class="g-form-section">
				<div class="g-form-group">
					<div v-for="(folder, index) in folders" :key="folder.name" class="g-form-row">
						<template v-if="renaming === folder.name">
							<GInput
								v-model="renameTo"
								:aria-label="__('Folder name')"
								:maxlength="80"
								@keydown.enter="saveRename(folder)"
							/>
							<GButton
								:label="__('Save')"
								:pending="busy"
								:disabled="busy || !renameTo.trim()"
								:aria-describedby="renameTo.trim() ? undefined : renameHintId"
								@click="saveRename(folder)"
							/>
							<GGhostButton :label="__('Cancel')" @click="renaming = null" />
						</template>
						<template v-else>
							<GListRow
								class="!px-0"
								:label="folder.folder_name"
								:sublabel="sopCount(folder.count)"
								:chevron="false"
								:aria-label="__('Rename {0}', [folder.folder_name])"
								@click="startRename(folder)"
							/>
							<GIconButton
								class="!flex-none"
								:label="__('Move {0} up', [folder.folder_name])"
								:disabled="index === 0"
								@click="move(folder, 'up')"
							>
								<ChevronUp class="h-5 w-5" aria-hidden="true" />
							</GIconButton>
							<GIconButton
								class="!flex-none"
								:label="__('Move {0} down', [folder.folder_name])"
								:disabled="index === folders.length - 1"
								@click="move(folder, 'down')"
							>
								<ChevronDown class="h-5 w-5" aria-hidden="true" />
							</GIconButton>
							<button
								v-if="folder.count === 0"
								type="button"
								class="g-form-row--action g-form-row--destructive !flex-none !w-auto min-h-11"
								:aria-label="__('Delete {0}', [folder.folder_name])"
								:disabled="busy"
								@click="deleting = folder"
							>
								{{ __("Delete") }}
							</button>
						</template>
					</div>
				</div>
				<!-- a dimmed Save says why, visibly and to a screen reader -->
				<p
					v-if="renaming && !renameTo.trim()"
					:id="renameHintId"
					class="g-form-footer"
					aria-live="polite"
				>
					{{ __("Name the folder") }}
				</p>
				<p class="g-form-footer">
					{{ __("A folder with SOPs in it cannot be deleted. Move its SOPs first.") }}
				</p>
			</section>
		</div>
	</GModal>

	<GConfirm
		:is-open="!!deleting"
		:title="__('Delete “{0}”?', [deleting?.folder_name || ''])"
		:confirm-label="__('Delete')"
		destructive
		:pending="busy"
		@confirm="remove"
		@cancel="deleting = null"
	>
		{{ __("The folder goes. No SOP is in it.") }}
	</GConfirm>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { ChevronDown, ChevronUp } from "lucide-vue-next"
import { computed, inject, ref, useId } from "vue"

import GButton from "@/components/glass/GButton.vue"
import GConfirm from "@/components/glass/GConfirm.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GInput from "@/components/glass/GInput.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import { gToast } from "@/components/glass/toast"
import { saveFailedSentence } from "@/utils/loudRequest"

const __ = inject("$translate")

// `sops` is the list page's get_sops resource: HR's answer lists every
// folder, empty ones too, with its count
const props = defineProps({
	open: { type: Boolean, default: false },
	sops: { type: Object, required: true },
})
const emit = defineEmits(["update:open"])

const folders = computed(() => props.sops.data?.folders || [])
const busy = ref(false)
const renaming = ref(null)
const renameTo = ref("")
const deleting = ref(null)
const renameHintId = useId()

const saveFolder = createResource({ url: "hrms.api.sop.save_folder" })
const moveFolder = createResource({ url: "hrms.api.sop.move_folder" })
const deleteFolder = createResource({ url: "hrms.api.sop.delete_folder" })

const sopCount = (n) => (n === 1 ? __("1 SOP") : __("{0} SOPs", [n]))

const close = () => {
	renaming.value = null
	emit("update:open", false)
}

// one change at a time; the list reloads after each, so the order and counts
// shown are always the server's
const run = async (request, params) => {
	if (busy.value) return false
	busy.value = true
	try {
		await request.fetch(params)
		await props.sops.reload()
		return true
	} catch (error) {
		console.warn("[SOP] Folder change failed:", error)
		gToast({
			title: __("Error"),
			text: saveFailedSentence(error, __("Could not change the folder")),
			variant: "error",
		})
		return false
	} finally {
		busy.value = false
	}
}

const startRename = (folder) => {
	renaming.value = folder.name
	renameTo.value = folder.folder_name
}

const saveRename = async (folder) => {
	const name = renameTo.value.trim()
	if (!name || busy.value) return
	if (name === folder.folder_name) {
		renaming.value = null
		return
	}
	if (await run(saveFolder, { folder_name: name, name: folder.name })) renaming.value = null
}

const move = (folder, direction) => run(moveFolder, { name: folder.name, direction })

const remove = async () => {
	if (await run(deleteFolder, { name: deleting.value.name })) deleting.value = null
}
</script>
