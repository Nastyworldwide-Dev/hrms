<template>
	<div class="flex flex-col h-full w-full bg-ground">
		<header
			class="flex flex-row items-center gap-2.5 bg-ground border-b-2 border-divider py-3.5 px-4 flex-none lg:h-16 lg:px-7 lg:py-0"
		>
			<button
				type="button"
				class="flex h-11 w-11 -my-2 -ml-3 items-center justify-center text-inkbase"
				:aria-label="__('Back')"
				@click="goBackOrHome(router)"
			>
				<FeatherIcon name="chevron-left" class="h-5 w-5" />
			</button>
			<h2
				class="text-base font-extrabold tracking-tight text-inkbase truncate"
			>
				{{ sop.data?.title || __("SOP") }}
			</h2>
			<button
				v-if="isHR"
				type="button"
				class="ml-auto flex h-11 w-11 -my-2 -mr-2 flex-none items-center justify-center text-accent-700"
				:aria-label="__('Edit {0}', [sop.data?.title || __('SOP')])"
				@click="sheetOpen = true"
			>
				<FeatherIcon name="edit" class="h-[17px] w-[17px]" />
			</button>
		</header>

		<div class="grow overflow-y-auto">
			<div
				v-if="sop.data"
				class="flex flex-col gap-3.5 w-full max-w-[820px] mx-auto px-4 pt-[18px] pb-16 lg:my-8 lg:bg-surface lg:border lg:border-divider lg:shadow-sm lg:px-14 lg:py-11"
			>
				<!-- meta -->
				<div class="flex items-center gap-2 flex-wrap">
					<span
						class="m-chip"
						:class="isGeneral ? 'm-chip-solid' : 'm-chip-outline'"
					>
						{{ isGeneral ? __("General") : sop.data.department }}
					</span>
					<span
						v-if="!sop.data.published"
						class="m-chip m-chip-muted !text-ink-700"
					>
						{{ __("Draft") }}
					</span>
					<span class="text-[11px] text-ink-700">
						{{ __("Updated") }} {{ dayjs(sop.data.modified).format("D MMM YYYY") }}
					</span>
				</div>

				<!-- body -->
				<div v-if="sop.data.content" class="sop-prose" v-html="sop.data.content"></div>

				<!-- attachment -->
				<div v-if="attachment" class="flex flex-col gap-2">
					<span class="m-kicker">{{ __("Attachment") }}</span>
					<div class="border border-divider">
						<div
							class="flex items-center gap-2.5 bg-surface border-b border-divider px-3 py-2.5"
						>
							<FeatherIcon
								name="file-text"
								class="h-[18px] w-[18px] flex-none text-accent-700"
							/>
							<span class="flex-1 text-[12.5px] font-bold text-inkbase truncate">
								{{ attachment.file_name }}
							</span>
							<a
								:href="attachment.file_url"
								target="_blank"
								rel="noopener"
								class="relative flex-none inline-flex h-[30px] w-[30px] items-center justify-center border border-accent text-accent no-underline before:absolute before:-inset-2 before:content-['']"
								:title="__('Download')"
								:aria-label="__('Download')"
							>
								<FeatherIcon name="download" class="h-3.5 w-3.5" />
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

			<EmptyState
				v-else-if="!sop.loading"
				:message="__('This SOP is not available')"
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
</template>

<script setup>
import { createResource, FeatherIcon } from "frappe-ui"
import { computed, inject, ref } from "vue"
import { useRouter } from "vue-router"

import PdfInlineViewer from "@/components/PdfInlineViewer.vue"
import SopFormSheet from "./SopFormSheet.vue"
import { goBackOrHome } from "@/utils/navigation"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const router = useRouter()

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
	color: var(--color-neutral-800);
}
.sop-prose :deep(h1),
.sop-prose :deep(h2),
.sop-prose :deep(h3),
.sop-prose :deep(h4),
.sop-prose :deep(h5),
.sop-prose :deep(h6) {
	font-family: var(--font-heading);
	font-weight: 800;
	color: var(--color-text);
	margin: 22px 0 6px;
	line-height: 1.3;
}
.sop-prose :deep(h1) {
	font-size: 19px;
	padding-bottom: 6px;
	border-bottom: 2px solid var(--color-divider);
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
	text-transform: uppercase;
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
	color: var(--color-text);
}
.sop-prose :deep(a) {
	color: var(--color-accent);
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
	color: var(--color-accent);
	font-weight: 700;
}
.sop-prose :deep(li > ul),
.sop-prose :deep(li > ol) {
	margin: 5px 0 0;
}
.sop-prose :deep(blockquote) {
	margin: 0 0 12px;
	padding: 6px 0 6px 14px;
	border-left: 3px solid var(--color-accent);
	color: var(--color-neutral-700);
	font-style: italic;
}
.sop-prose :deep(hr) {
	border: 0;
	border-top: 2px solid var(--color-divider);
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
	font-family: var(--font-heading);
	font-weight: 800;
	font-size: 11px;
	text-transform: uppercase;
	letter-spacing: 0.05em;
	text-align: left;
	color: var(--color-text);
	border-bottom: 2px solid var(--color-text);
	padding: 7px 10px 7px 0;
}
.sop-prose :deep(td) {
	border-bottom: 1px solid var(--color-divider);
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
	background: var(--color-neutral-100);
	padding: 2px 5px;
}
.sop-prose :deep(pre) {
	padding: 10px 12px;
	overflow-x: auto;
	margin: 0 0 12px;
}
</style>
