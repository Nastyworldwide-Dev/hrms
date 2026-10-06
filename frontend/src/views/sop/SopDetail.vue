<template>
	<GPage>
	<div class="flex flex-col h-full w-full bg-ground g-page__content">
		<!-- The one header (alpha.5); HR's Edit takes the bell/avatar slot. -->
		<ShellHeader bare :title="sop.data?.title || __('SOP')">
			<template v-if="isHR" #actions>
				<GIconButton
					:label="__('Edit {0}', [sop.data?.title || __('SOP')])"
					class="text-accent-700"
					@click="sheetOpen = true"
				>
					<PenLine class="h-icon-md w-icon-md" />
				</GIconButton>
			</template>
		</ShellHeader>

		<div class="grow overflow-y-auto">
			<ResourceError :resource="sop" what="this document" />
			<div
				v-if="sop.data"
				class="flex flex-col gap-3.5 w-full max-w-content-column-read mx-auto px-4 pt-4 pb-16 lg:my-8 lg:bg-surface lg:border lg:border-divider lg:shadow-sm lg:px-14 lg:py-11"
			>
				<!-- meta -->
				<div class="flex items-center gap-2 flex-wrap">
					<GBadge :variant="isGeneral ? 'open' : 'accent'">
						{{ isGeneral ? __("General") : departmentLabel(sop.data.department) }}
					</GBadge>
					<GBadge v-if="!sop.data.published" variant="neutral" class="!text-ink-700">
						{{ __("Draft") }}
					</GBadge>
					<span class="text-kra-label text-ink-700">
						{{ __("Updated") }} {{ dayjs(sop.data.modified).format("D MMM YYYY") }}
					</span>
				</div>

				<!-- body -->
				<div v-if="sop.data.content" class="sop-prose" v-html="safeHtml(sop.data.content)"></div>

				<!-- attachment -->
				<div v-if="attachment" class="flex flex-col gap-2">
					<span class="g-eyebrow">{{ __("Attachment") }}</span>
					<div class="border border-divider rounded-panel overflow-hidden">
						<div class="flex items-center gap-2.5 bg-surface border-b border-divider px-3 py-2.5">
							<FileText class="h-icon-md w-icon-md flex-none text-accent-700" />
							<span class="flex-1 text-card-title font-bold text-inkbase truncate">
								{{ attachment.file_name }}
							</span>
							<a
								:href="attachment.file_url"
								target="_blank"
								rel="noopener"
								class="relative flex-none inline-flex h-icon-xl w-icon-xl items-center justify-center border border-accent-ink text-accent-ink no-underline before:absolute before:-inset-2 before:content-['']"
								:title="__('Download')"
								:aria-label="__('Download')"
							>
								<Download class="h-3.5 w-3.5" />
							</a>
						</div>

						<img
							v-if="attachmentKind === 'image'"
							:src="attachment.file_url"
							:alt="attachment.file_name"
							class="block w-full"
						/>
						<PdfInlineViewer
							v-else-if="attachmentKind === 'pdf'"
							:fileUrl="attachment.content_url || attachment.file_url"
						/>
					</div>
				</div>
			</div>

			<GEmptyState
				v-else-if="!sop.loading && !sop.error"
				:title="__('Nothing to show yet')"
				:body="__('This procedure has no content published')"
			/>
		</div>

		<SopFormSheet
			v-if="isHR"
			:open="sheetOpen"
			:sopName="props.id"
			@update:open="sheetOpen = $event"
			@saved="sop.reload()"
		/>
	</div>
	</GPage>
</template>

<script setup>
import { departmentLabel } from "@/utils/departmentLabel"
import { safeHtml } from "@/utils/safeHtml"
import { Download, FileText, PenLine } from "lucide-vue-next"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GBadge from "@/components/glass/GBadge.vue"
import { createResource } from "frappe-ui"
import { computed, inject, ref } from "vue"

import PdfInlineViewer from "@/components/PdfInlineViewer.vue"
import SopFormSheet from "./SopFormSheet.vue"
import GPage from "@/components/glass/GPage.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import ShellHeader from "@/components/ShellHeader.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const props = defineProps({
	id: { type: String, required: true },
})

const sop = createResource({
	url: "hrms.api.sop.get_sop",
	params: { name: props.id },
	auto: true,
	onError(error) {
		console.warn("[SOP] Failed to load:", error)
	},
})

const sheetOpen = ref(false)

const isGeneral = computed(() => sop.data?.scope !== "Department")
// server-declared flag — same source of truth as the list payload
const isHR = computed(() => !!sop.data?.is_hr)
const attachment = computed(() => sop.data?.attachment || null)

// inline full view: images and PDFs render in place, everything else falls
// back to the header row's download button
const attachmentKind = computed(() => {
	const url = attachment.value?.file_url || ""
	if (/\.(gif|jpe?g|png|svg|webp)(\?|$)/i.test(url)) return "image"
	if (/\.pdf(\?|$)/i.test(url)) return "pdf"
	return "other"
})
</script>
