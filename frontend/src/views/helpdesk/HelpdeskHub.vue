<template>
	<BaseLayout :pageTitle="__('Helpdesk')">
		<template #body>
			<!-- ONE page, two pills (owner, 15 Sep 2026): HR Issues for everyone,
			     IT Helpdesk where the Helpdesk app is installed. Each pill renders
			     the list that used to be its own page; the page chrome is here. -->
			<!-- GSegmented draws nothing for a single option (8.8), so on a site
			     without the Helpdesk app the row must go too, not leave a spacer -->
			<div
				v-if="tabButtons.length > 1"
				class="px-4 pt-4 w-full lg:px-7 lg:pt-6 max-w-content-column-lg mx-auto"
			>
				<GSegmented
					:modelValue="tab"
					:buttons="tabButtons"
					:label="__('Helpdesk section')"
					@update:modelValue="selectTab"
				/>
			</div>
			<IssuesTab v-if="tab === HR_TAB" />
			<HelpdeskList v-else />
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import BaseLayout from "@/components/BaseLayout.vue"
import GSegmented from "@/components/glass/GSegmented.vue"
import { helpdeskAvailable } from "@/data/helpdesk"
import {
	HR_TAB,
	HUB_ROUTE_NAME,
	IT_TAB,
	TAB_STORAGE_KEY,
	parseTab,
	resolveTab,
} from "@/utils/helpdeskHub"
import IssuesTab from "@/views/issues/IssuesTab.vue"
import HelpdeskList from "./HelpdeskList.vue"

const __ = inject("$translate")
const route = useRoute()
const router = useRouter()

// storage is a convenience, never a dependency: private mode or a cleared
// site throws on access and the page must still open
const remembered = () => {
	try {
		return localStorage.getItem(TAB_STORAGE_KEY)
	} catch (e) {
		return null
	}
}
const remember = (value) => {
	try {
		localStorage.setItem(TAB_STORAGE_KEY, value)
	} catch (e) {
		// nothing to do — the URL still carries the pill
	}
}

// The IT pill exists only where the Helpdesk app is installed (nasty-live has
// none). helpdeskAvailable is auto-fetched and cached, but its data is NULL
// until the cache hydrates or the probe answers — and setup runs before
// either. Only an ANSWERED false removes the pill: treating "not yet" as
// "no" clamped a cold ?tab=it to hr and rewrote the URL before the probe
// could say yes (review of 8b38ddfc8), losing every IT deep link on reload.
const itRefused = computed(() => helpdeskAvailable.data === false)
const tabButtons = computed(() => [
	{ key: HR_TAB, label: __("HR Issues") },
	...(itRefused.value ? [] : [{ key: IT_TAB, label: __("IT Helpdesk") }]),
])

// Which pill a request asks for, clamped to what this site offers.
const clamp = (value) => (value === IT_TAB && itRefused.value ? HR_TAB : value)

// DECLARED BEFORE THE WATCHES BELOW, on purpose (the KPI dashboard's TDZ
// lesson: a watch getter runs synchronously at setup, and a `const` further
// down would throw "before initialization" and leave Ionic holding a view
// with no element). Query wins, then the remembered pill, then HR Issues.
const tab = ref(clamp(resolveTab(route.query.tab, remembered())))

// The URL always states the pill: a bare /support (sidebar, More) is rewritten
// in place so a share, a reload or BACK from a ticket lands on the same view.
// replace, not push — switching pills must not stack history entries, or BACK
// would walk the pills instead of leaving the page.
const syncQuery = (value) => {
	if (route.name !== HUB_ROUTE_NAME || route.query.tab === value) return
	router.replace({ query: { ...route.query, tab: value } })
}

const selectTab = (value) => {
	const next = clamp(parseTab(value) ?? HR_TAB)
	console.info("[HelpdeskHub] pill:", next)
	tab.value = next
	remember(next)
	syncQuery(next)
}

// A deep link while the page is already mounted (Home → "HR Issues" from the
// IT pill; the tab shell reuses this instance for a same-path navigation),
// or BACK/FORWARD across two pill states.
watch(
	() => route.query.tab,
	(value) => {
		if (route.name !== HUB_ROUTE_NAME) return
		const next = clamp(resolveTab(value, remembered()))
		if (next !== tab.value) tab.value = next
		syncQuery(next)
	}
)

// after mount, not in setup: a replace while the outlet is still mounting
// this page would cancel the very navigation that is showing it
onMounted(() => {
	console.info("[HelpdeskHub] opened on pill:", tab.value)
	syncQuery(tab.value)
})

// The availability probe can answer AFTER setup: a cached "it" pill on a site
// that lost the app clamps back to HR Issues instead of a pill that is not drawn.
watch(itRefused, () => {
	const next = clamp(tab.value)
	if (next !== tab.value) selectTab(next)
})
</script>
