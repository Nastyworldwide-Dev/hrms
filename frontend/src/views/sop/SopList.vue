<template>
	<!-- On the kit (owner, 25 Sep 2026: hand-rolled screens): sections of rows
	     in inset groups, the new-SOP action a bar button. It was lime tiles, a
	     ruled list and a floating lime square. -->
	<BaseLayout :pageTitle="__('SOPs')">
		<template v-if="isHR" #actions>
			<GIconButton :label="__('New SOP')" @click="openCreate">
				<Plus class="h-5 w-5" aria-hidden="true" />
			</GIconButton>
		</template>
		<template #body>
			<div class="g-form-body w-full max-w-content-column-lg mx-auto">
				<!-- SEARCH FIRST. An SOP library is a lookup tool, not a browse
				     tool: somebody opening it is usually after one document they
				     half remember. GSearchBar, never a hand-built input. -->
				<GSearchBar
					v-model="typed"
					:placeholder="__('Search SOPs')"
					:label="__('Search SOPs')"
					@clear="typed = ''"
				/>

				<!-- Essentials (pinned) first, then each section, as iOS sections. -->
				<section v-if="pinned.length" class="g-form-section">
					<h2 class="g-form-section__title">{{ __("Essentials") }}</h2>
					<GListPanel>
						<GListRow
							v-for="sop in pinned"
							:key="sop.name"
							:label="sop.title"
							:sublabel="scopeLabel(sop)"
							:tint="TILE.sop"
							@click="openSop(sop)"
						>
							<template #icon><BookOpen class="g-row-icon" /></template>
						</GListRow>
					</GListPanel>
				</section>

				<template v-if="!isEmpty">
					<section v-for="section in sections" :key="section.key" class="g-form-section">
						<h2 class="g-form-section__title">{{ sectionLabel(section) }}</h2>
						<GListPanel>
							<GListRow
								v-for="sop in section.sops"
								:key="sop.name"
								:label="sop.title"
								:sublabel="rowLine(sop)"
								@click="openSop(sop)"
							>
								<template v-if="!sop.published" #badge>
									<GBadge variant="neutral">{{ __("Draft") }}</GBadge>
								</template>
							</GListRow>
						</GListPanel>
					</section>
				</template>

				<GEmptyState
					v-else-if="query"
					:title="__('No SOPs match “{0}”', [query])"
					:body="__('Try a different search term.')"
				/>
				<ResourceError v-else-if="sops.error" :resource="sops" what="the SOP list" />
				<GEmptyState
					v-else-if="!sops.loading"
					:title="__('No SOPs yet')"
					:body="__('Procedures for your role will appear here')"
				/>
			</div>

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
import { BookOpen, Plus } from "lucide-vue-next"
import { useRouter } from "vue-router"
import { TILE } from "@/utils/iconTile"
import GIconButton from "@/components/glass/GIconButton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import { personalCacheKey } from "@/utils/personalCache"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import { createResource } from "frappe-ui"
import { computed, inject, onBeforeUnmount, ref, watch } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"
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

const router = useRouter()
//: Every row reads the SOP; HR edits from its page (SopDetail's Edit).
const openSop = (sop) => router.push({ name: "SopDetailView", params: { id: sop.name } })
const rowLine = (sop) => `${__("Updated")} ${dayjs(sop.modified).format("D MMM YYYY")}`

const openCreate = () => {
	editingName.value = null
	sheetOpen.value = true
}
</script>
