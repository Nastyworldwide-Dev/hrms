<template>
	<BaseLayout :pageTitle="__('SOPs')">
		<template #body>
			<div
				class="flex flex-col gap-4 w-full max-w-content-column-lg mx-auto px-4 pt-4 pb-24 lg:p-7"
			>
				<!-- Essentials (pinned) -->
				<div v-if="isHR || pinned.length" class="flex flex-col gap-2.5">
					<div class="flex items-center justify-between">
						<span v-if="pinned.length" class="g-eyebrow">{{ __("Essentials") }}</span>
						<span v-else></span>
						<GBadge v-if="isHR" variant="accent">{{ __("HR") }}</GBadge>
					</div>
					<div v-if="pinned.length" class="grid grid-cols-2 gap-2.5">
						<router-link
							v-for="sop in pinned"
							:key="sop.name"
							:to="{ name: 'SopDetailView', params: { id: sop.name } }"
							class="relative flex flex-col gap-4 bg-accent-ink text-ground p-3 no-underline active:scale-[0.97] active:bg-accent-600"
							style="
								transition: transform var(--g-motion-button-press-duration)
										var(--g-motion-button-press-easing),
									background-color var(--g-motion-button-press-duration)
										var(--g-motion-button-press-easing);
							"
						>
							<BookOpen class="h-icon-lg w-icon-lg flex-none" />
							<button
								v-if="isHR"
								type="button"
								class="absolute right-0 top-0 flex h-11 w-11 items-center justify-center text-ground"
								:aria-label="__('Edit {0}', [sop.title])"
								@click.prevent.stop="openEdit(sop)"
							>
								<PenLine class="h-icon-sm w-icon-sm" />
							</button>
							<span class="flex flex-col gap-0.5">
								<span class="font-extrabold text-card-title leading-tight">
									{{ sop.title }}
								</span>
								<span class="g-eyebrow font-bold opacity-75">
									{{ scopeLabel(sop) }}
								</span>
							</span>
						</router-link>
					</div>
				</div>

				<!-- SEARCH FIRST. An SOP library is a lookup tool, not a browse
				     tool: somebody opening it is usually after one document they
				     half remember, and a list of sections is not how they find
				     it.

				     GSearchBar, not a hand-built input. The system already had
				     one — with the clear control and the two-tone focus ring —
				     and this screen grew its own, which is the drift the usage
				     gate exists to catch and did not, because an <input> is not
				     a G* component being bypassed. It carries 20 of the app's
				     103 stray pixel values for the same reason. -->
				<GSearchBar
					v-model="typed"
					:placeholder="__('Search SOPs…')"
					:label="__('Search SOPs')"
					@clear="typed = ''"
				/>

				<!-- Sections -->
				<div v-if="!isEmpty" class="flex flex-col gap-4">
					<div v-for="section in sections" :key="section.key" class="flex flex-col gap-2">
						<span class="g-eyebrow">{{ sectionLabel(section) }}</span>
						<div class="flex flex-col border-t-2 border-divider">
							<router-link
								v-for="sop in section.sops"
								:key="sop.name"
								:to="{ name: 'SopDetailView', params: { id: sop.name } }"
								class="flex items-center gap-2.5 bg-surface border-b border-divider p-3 no-underline active:scale-[0.985] active:bg-ink-200"
								style="
									transition: transform var(--g-motion-button-press-duration)
											var(--g-motion-button-press-easing),
										background-color var(--g-motion-button-press-duration)
											var(--g-motion-button-press-easing);
								"
							>
								<span class="flex flex-col gap-0.5 flex-1 min-w-0">
									<span class="flex items-center gap-1.5 min-w-0">
										<span class="font-extrabold text-card-title text-inkbase truncate">
											{{ sop.title }}
										</span>
										<GBadge
											v-if="!sop.published"
											variant="neutral"
											class="!text-ink-700 flex-none"
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
									<PenLine class="h-icon-sm w-icon-sm" />
								</button>
								<ChevronRight class="h-4 w-4 flex-none text-ink-400" />
							</router-link>
						</div>
					</div>
				</div>

				<!-- Empty state -->
				<div
					v-else-if="query"
					class="flex flex-col items-center gap-2 px-5 py-11 text-center text-ink-600"
				>
					<Search class="h-icon-xl w-icon-xl text-ink-300" />
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
				class="fixed right-4 bottom-fab z-30 flex h-control-lg w-control-lg items-center justify-center bg-accent-ink text-ground shadow-md active:scale-90 lg:bottom-8"
				style="
					transition: transform var(--g-motion-button-press-duration)
						var(--g-motion-button-press-easing);
				"
				:aria-label="__('New SOP')"
				@click="openCreate"
			>
				<Plus class="h-icon-lg w-icon-lg" />
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
import { departmentLabel } from "@/utils/departmentLabel"
import { BookOpen, ChevronRight, PenLine, Plus, Search } from "lucide-vue-next"
import { personalCacheKey } from "@/utils/personalCache"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import { createResource } from "frappe-ui"
import { computed, inject, onBeforeUnmount, ref, watch } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import SopFormSheet from "./SopFormSheet.vue"

import { userResource } from "@/data/user"
import { hasHRRole } from "@/utils/issueBoard"
import { buildSopSections } from "@/utils/sopLibrary"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

//: TWO refs, and the difference is the feature. `typed` is what the person is
//: holding; `query` is what the list has been filtered by, and it follows
//: 300ms later.
//:
//: Searching on every keystroke re-filters and re-groups the whole library
//: between letters, so the list flickers through nonsense while somebody is
//: still typing a word. 300ms is the standard perceptual threshold (Nielsen,
//: Response Times) — below it a person does not notice the wait, above it
//: they do.
//: 300ms — the standard perceptual threshold (Nielsen, Response Times: The 3
//: Important Limits). Below it nobody notices the wait; above it they do.
const SEARCH_DEBOUNCE_MS = 300

const typed = ref("")
const query = ref("")
let debounce = null

watch(typed, (value) => {
	clearTimeout(debounce)
	// Clearing is INSTANT. A person who taps the × wants the full list back
	// now, and waiting 300ms to show them what they already had reads as lag.
	if (!value) {
		query.value = ""
		return
	}
	debounce = setTimeout(() => {
		query.value = value
	}, SEARCH_DEBOUNCE_MS)
})

onBeforeUnmount(() => clearTimeout(debounce))
const sheetOpen = ref(false)
const editingName = ref(null)

// the server scopes rows (published + General + own department, everything for
// HR) — the client only groups and searches what it is given
const sops = createResource({
	url: "hrms.api.sop.get_sops",
	cache: personalCacheKey("hrms:sops"),
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
	sop.scope === "Department" && sop.department ? departmentLabel(sop.department) : __("General")

const sectionLabel = (section) => {
	if (!section.department) return __("General")
	// an employee only ever gets their own department group — name it as such;
	// HR gets every department, where the plain name reads better
	const name = departmentLabel(section.department)
	return isHR.value ? name : __("My Department — {0}", [name])
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
