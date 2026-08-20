<template>
	<BaseLayout :pageTitle="__('SOPs')">
		<template #body>
			<div
				class="flex flex-col gap-[18px] w-full max-w-content-column-lg mx-auto px-4 pt-[18px] pb-24 lg:p-7"
			>
				<!-- Essentials (pinned) -->
				<div v-if="isHR || pinned.length" class="flex flex-col gap-2.5">
					<div class="flex items-center justify-between">
						<span v-if="pinned.length" class="text-eyebrow uppercase text-accent-ink">{{ __("Essentials") }}</span>
						<span v-else></span>
						<GBadge v-if="isHR" variant="accent">{{ __("HR") }}</GBadge>
					</div>
					<div v-if="pinned.length" class="grid grid-cols-2 gap-2.5">
						<router-link
							v-for="sop in pinned"
							:key="sop.name"
							:to="{ name: 'SopDetailView', params: { id: sop.name } }"
							class="relative flex flex-col gap-[18px] bg-accent text-ground p-3 no-underline active:scale-[0.97] active:bg-accent-600"
							style="
								transition: transform var(--motion-press), background-color var(--motion-press);
							"
						>
							<FeatherIcon name="book-open" class="h-[22px] w-[22px] flex-none" />
							<button
								v-if="isHR"
								type="button"
								class="absolute right-0 top-0 flex h-11 w-11 items-center justify-center text-ground"
								:aria-label="__('Edit {0}', [sop.title])"
								@click.prevent.stop="openEdit(sop)"
							>
								<FeatherIcon name="edit" class="h-[15px] w-[15px]" />
							</button>
							<span class="flex flex-col gap-0.5">
								<span class="font-extrabold text-card-title leading-tight">
									{{ sop.title }}
								</span>
								<span class="text-micro-label uppercase font-bold opacity-75">
									{{ scopeLabel(sop) }}
								</span>
							</span>
						</router-link>
					</div>
				</div>

				<!-- Search -->
				<div class="relative">
					<FeatherIcon
						name="search"
						class="absolute left-2.5 top-1/2 -translate-y-1/2 h-[15px] w-[15px] text-ink-500 pointer-events-none"
					/>
					<input
						v-model="query"
						:placeholder="__('Search SOPs…')"
						:aria-label="__('Search SOPs')"
						class="w-full bg-surface border border-divider py-2.5 pl-[34px] pr-3 text-card-title text-inkbase placeholder:text-ink-500 focus:outline-none focus:border-accent focus:shadow-[0_0_0_2px_rgba(11,49,58,0.12)]"
					/>
				</div>

				<!-- Sections -->
				<div v-if="!isEmpty" class="flex flex-col gap-[18px]">
					<div v-for="section in sections" :key="section.key" class="flex flex-col gap-2">
						<span class="text-eyebrow uppercase text-accent-ink">{{ sectionLabel(section) }}</span>
						<div class="flex flex-col border-t-2 border-divider">
							<router-link
								v-for="sop in section.sops"
								:key="sop.name"
								:to="{ name: 'SopDetailView', params: { id: sop.name } }"
								class="flex items-center gap-2.5 bg-surface border-b border-divider p-3 no-underline active:scale-[0.985] active:bg-ink-200"
								style="
									transition: transform var(--motion-press), background-color var(--motion-press);
								"
							>
								<span class="flex flex-col gap-0.5 flex-1 min-w-0">
									<span class="flex items-center gap-1.5 min-w-0">
										<span class="font-extrabold text-card-title text-inkbase truncate">
											{{ sop.title }}
										</span>
										<GBadge
											v-if="!sop.published"
											variant="neutral" class="!text-ink-700 flex-none"
										>
											{{ __("Draft") }}
										</GBadge>
									</span>
									<span class="text-kra-label text-ink-700">
										{{ __("Updated") }} {{ dayjs(sop.modified).format("D MMM YYYY") }}
									</span>
								</span>
								<button
									v-if="isHR"
									type="button"
									class="flex-none flex h-11 w-11 -my-2.5 -mr-1.5 items-center justify-center text-accent-700"
									:aria-label="__('Edit {0}', [sop.title])"
									@click.prevent.stop="openEdit(sop)"
								>
									<FeatherIcon name="edit" class="h-[15px] w-[15px]" />
								</button>
								<FeatherIcon name="chevron-right" class="h-4 w-4 flex-none text-ink-400" />
							</router-link>
						</div>
					</div>
				</div>

				<!-- Empty state -->
				<div
					v-else-if="query"
					class="flex flex-col items-center gap-2 px-5 py-11 text-center text-ink-600"
				>
					<FeatherIcon name="search" class="h-[34px] w-[34px] text-ink-300" />
					<div class="text-card-title">
						{{ __("No SOPs match “{0}”.", [query]) }}<br />
						{{ __("Try a different search term.") }}
					</div>
				</div>
				<ResourceError v-else-if="sops.error" :resource="sops" what="the SOP list" />
				<GEmptyState
					v-else-if="!sops.loading"
					:title="__('No documents yet')"
					:body="__('Procedures for your role will appear here')"
				/>
			</div>

			<!-- HR: create -->
			<button
				v-if="isHR"
				type="button"
				class="fixed right-4 bottom-[76px] z-30 flex h-[52px] w-[52px] items-center justify-center bg-accent text-ground shadow-md active:scale-90 lg:bottom-8"
				style="transition: transform var(--motion-press)"
				:aria-label="__('New SOP')"
				@click="openCreate"
			>
				<FeatherIcon name="plus" class="h-[22px] w-[22px]" />
			</button>

			<SopFormSheet
				v-if="isHR"
				:open="sheetOpen"
				:sopName="editingName"
				@update:open="sheetOpen = $event"
				@saved="sops.reload()"
			/>
		</template>
	</BaseLayout>
</template>

<script setup>
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GBadge from "@/components/glass/GBadge.vue"
import { createResource, FeatherIcon } from "frappe-ui"
import { computed, inject, ref } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import SopFormSheet from "./SopFormSheet.vue"

import { userResource } from "@/data/user"
import { hasHRRole } from "@/utils/issueBoard"
import { buildSopSections } from "@/utils/sopLibrary"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const query = ref("")
const sheetOpen = ref(false)
const editingName = ref(null)

// the server scopes rows (published + General + own department, everything for
// HR) — the client only groups and searches what it is given
const sops = createResource({
	url: "hrms.api.sop.get_sops",
	cache: "hrms:sops",
	auto: true,
	onError(error) {
		console.warn("[SOP] Failed to load:", error)
	},
})

// the payload's is_hr is the single source of truth; the user flag (computed
// server-side from the same HR_ROLES rule) only covers the first paint,
// before the request lands
const isHR = computed(() => (sops.data ? !!sops.data.is_hr : hasHRRole(userResource.data)))

const grouped = computed(() => buildSopSections(sops.data, query.value))
const pinned = computed(() => grouped.value.pinned)
const sections = computed(() => grouped.value.sections)
const isEmpty = computed(() => grouped.value.isEmpty)

const scopeLabel = (sop) =>
	sop.scope === "Department" && sop.department ? sop.department : __("General")

const sectionLabel = (section) => {
	if (!section.department) return __("General")
	// an employee only ever gets their own department group — name it as such;
	// HR gets every department, where the plain name reads better
	return isHR.value ? section.department : __("My Department — {0}", [section.department])
}

const openCreate = () => {
	editingName.value = null
	sheetOpen.value = true
}

const openEdit = (sop) => {
	console.info("[SOP] editing:", sop.name)
	editingName.value = sop.name
	sheetOpen.value = true
}
</script>
