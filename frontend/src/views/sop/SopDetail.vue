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

<style scoped>
/* document-grade rendering for the Text Editor body — headings, lists,
   tables and quotes read like a print format, not chat text */
.sop-prose {
	font-size: 13.5px;
	line-height: 1.75;
	color: var(--g-ink2);
}
.sop-prose :deep(h1),
.sop-prose :deep(h2),
.sop-prose :deep(h3),
.sop-prose :deep(h4),
.sop-prose :deep(h5),
.sop-prose :deep(h6) {
	font-family: var(--g-font-display);
	font-weight: 800;
	color: var(--g-ink);
	margin: 22px 0 6px;
	line-height: 1.3;
}
.sop-prose :deep(h1) {
	font-size: 19px;
	padding-bottom: 6px;
	border-bottom: 2px solid var(--g-hair);
}
.sop-prose :deep(h2) {
	font-size: 16px;
}
.sop-prose :deep(h3) {
	font-size: 14.5px;
}
.sop-prose :deep(h4),
.sop-prose :deep(h5),
.sop-prose :deep(h6) {
	font-size: 13.5px;
	letter-spacing: 0.04em;
}
.sop-prose :deep(h1:first-child),
.sop-prose :deep(h2:first-child),
.sop-prose :deep(h3:first-child),
.sop-prose :deep(p:first-child) {
	margin-top: 0;
}
.sop-prose :deep(p) {
	margin: 0 0 10px;
}
.sop-prose :deep(strong),
.sop-prose :deep(b) {
	font-weight: 700;
	color: var(--g-ink);
}
.sop-prose :deep(a) {
	color: var(--g-accent-ink);
	text-decoration: underline;
}
.sop-prose :deep(ul),
.sop-prose :deep(ol) {
	margin: 0 0 12px;
	padding-left: 22px;
	display: flex;
	flex-direction: column;
	gap: 5px;
}
.sop-prose :deep(ul) {
	list-style: square;
}
.sop-prose :deep(ol) {
	list-style: decimal;
}
.sop-prose :deep(li)::marker {
	color: var(--g-accent-ink);
	font-weight: 700;
}
.sop-prose :deep(li > ul),
.sop-prose :deep(li > ol) {
	margin: 5px 0 0;
}
.sop-prose :deep(blockquote) {
	margin: 0 0 12px;
	padding: 6px 0 6px 14px;
	border-left: 3px solid var(--g-accent-ink);
	color: var(--g-ink2);
}
.sop-prose :deep(hr) {
	border: 0;
	border-top: 2px solid var(--g-hair);
	margin: 18px 0;
}
.sop-prose :deep(table) {
	width: 100%;
	border-collapse: collapse;
	margin: 4px 0 14px;
	font-size: 12.5px;
	display: block;
	overflow-x: auto;
}
.sop-prose :deep(th) {
	font-family: var(--g-font-display);
	font-weight: 800;
	font-size: 11px;
	letter-spacing: 0.05em;
	text-align: left;
	color: var(--g-ink);
	border-bottom: 2px solid var(--g-ink);
	padding: 7px 10px 7px 0;
}
.sop-prose :deep(td) {
	border-bottom: 1px solid var(--g-hair);
	padding: 7px 10px 7px 0;
	vertical-align: top;
}
.sop-prose :deep(img) {
	max-width: 100%;
	height: auto;
	margin: 4px 0 12px;
}
.sop-prose :deep(pre),
.sop-prose :deep(code) {
	font-size: 12px;
	background: var(--g-icon-bg);
	padding: 2px 5px;
}
.sop-prose :deep(pre) {
	padding: 10px 12px;
	overflow-x: auto;
	margin: 0 0 12px;
}
</style>
