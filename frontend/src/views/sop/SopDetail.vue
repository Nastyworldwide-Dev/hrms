<template>
	<div class="flex flex-col h-full w-full bg-ground">
		<header
			class="flex flex-row items-center gap-2.5 bg-ground border-b-2 border-divider py-3.5 px-4 flex-none lg:h-16 lg:px-7 lg:py-0"
		>
			<button
				type="button"
				class="flex p-1 -ml-1 text-inkbase"
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
		</header>

		<div class="grow overflow-y-auto">
			<div
				v-if="sop.data"
				class="flex flex-col gap-3.5 w-full max-w-[720px] px-4 pt-[18px] pb-16 lg:p-7"
			>
				<!-- meta -->
				<div class="flex items-center gap-2 flex-wrap">
					<span
						class="m-chip"
						:class="isGeneral ? 'm-chip-solid' : 'm-chip-outline'"
					>
						{{ isGeneral ? __("General") : sop.data.department }}
					</span>
					<span v-if="!sop.data.published" class="m-chip m-chip-muted">
						{{ __("Draft") }}
					</span>
					<span class="text-[11px] text-ink-600">
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
								class="flex-none inline-flex h-[30px] w-[30px] items-center justify-center border border-accent text-accent no-underline"
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
							:fileUrl="attachment.file_url"
						/>
					</div>
				</div>
			</div>

			<EmptyState
				v-else-if="!sop.loading"
				:message="__('This SOP is not available')"
			/>
		</div>
	</div>
</template>

<script setup>
import { createResource, FeatherIcon } from "frappe-ui"
import { computed, inject } from "vue"
import { useRouter } from "vue-router"

import PdfInlineViewer from "@/components/PdfInlineViewer.vue"
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

const isGeneral = computed(() => sop.data?.scope !== "Department")
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
/* mockup prose styling for the Text Editor body */
.sop-prose :deep(h1),
.sop-prose :deep(h2),
.sop-prose :deep(h3),
.sop-prose :deep(h4) {
	font-family: var(--font-heading);
	font-weight: 800;
	font-size: 14px;
	margin: 4px 0 0;
	color: var(--color-text);
}
.sop-prose :deep(p) {
	font-size: 13px;
	line-height: 1.6;
	color: var(--color-neutral-800);
	margin: 8px 0 0;
}
.sop-prose :deep(ul),
.sop-prose :deep(ol) {
	list-style: none;
	padding: 0;
	margin: 8px 0 0;
	display: flex;
	flex-direction: column;
	gap: 7px;
}
.sop-prose :deep(li) {
	position: relative;
	padding-left: 16px;
	font-size: 13px;
	line-height: 1.5;
	color: var(--color-neutral-800);
}
.sop-prose :deep(li)::before {
	content: "";
	position: absolute;
	left: 0;
	top: 6px;
	width: 6px;
	height: 6px;
	background: var(--color-accent-500);
}
.sop-prose :deep(img) {
	max-width: 100%;
	height: auto;
}
</style>
