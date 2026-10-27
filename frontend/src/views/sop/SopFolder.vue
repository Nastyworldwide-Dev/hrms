<template>
	<!-- One SOP folder (owner, 27 Oct 2026): the folder's SOPs as the list
	     shows them, from the same get_sops answer; no second fetch. -->
	<GPage>
		<div class="flex flex-col h-full w-full bg-ground g-page__content">
			<ShellHeader bare :title="folder?.folder_name || props.folder" />
			<div class="grow overflow-y-auto">
				<div class="g-form-body w-full max-w-content-column-lg mx-auto">
					<ResourceError v-if="sops.error" :resource="sops" what="the SOP list" />
					<section v-else-if="folder?.sops?.length" class="g-form-section">
						<GListPanel>
							<GListRow
								v-for="sop in folder.sops"
								:key="sop.name"
								:label="sop.title"
								:sublabel="`${__('Updated')} ${dayjs(sop.modified).format('D MMM YYYY')}`"
								@click="router.push({ name: 'SopDetailView', params: { id: sop.name } })"
							>
								<template v-if="!sop.published" #badge>
									<GBadge variant="neutral">{{ __("Draft") }}</GBadge>
								</template>
							</GListRow>
						</GListPanel>
					</section>
					<GEmptyState
						v-else-if="!sops.loading"
						:title="__('No SOPs in this folder yet')"
						:body="
							sops.data?.is_hr
								? __('Pick this folder when you write or edit an SOP.')
								: __('Check back soon.')
						"
					/>
				</div>
			</div>
		</div>
	</GPage>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { computed, inject } from "vue"
import { useRouter } from "vue-router"

import ResourceError from "@/components/ResourceError.vue"
import ShellHeader from "@/components/ShellHeader.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GPage from "@/components/glass/GPage.vue"
import { personalCacheKey } from "@/utils/personalCache"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const router = useRouter()

const props = defineProps({
	folder: { type: String, required: true },
})

// the same cache key as SopList, so frappe-ui hands back the list's resource
const sops = createResource({
	url: "hrms.api.sop.get_sops",
	cache: personalCacheKey("hrms:sops"),
	auto: true,
	onError(error) {
		console.warn("[SOP] Failed to load:", error)
	},
})

const folder = computed(() => (sops.data?.folders || []).find((f) => f.name === props.folder))
</script>
