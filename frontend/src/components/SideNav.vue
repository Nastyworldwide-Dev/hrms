<template>
	<aside
		class="g-sidenav hidden lg:flex flex-col flex-none overflow-hidden transition-[width] duration-200"
		:style="{ width: collapsed ? '72px' : '216px' }"
	>
		<!-- Logo header (64px) -->
		<div class="h-16 flex items-center gap-2.5 px-4 border-b-2 border-divider flex-none">
			<!-- Nadi mark: brand token colours (--g-brand / --g-on-brand), not the
			     asset's literal hex — one source for "what is brand lime" across
			     the whole glass surface system, not a second one per logo. -->
			<svg width="32" height="32" viewBox="0 0 32 32" fill="none" class="flex-none">
				<rect width="32" height="32" rx="8" fill="var(--g-brand)" />
				<text
					x="16"
					y="22"
					text-anchor="middle"
					font-family="Inter, system-ui, sans-serif"
					font-weight="800"
					font-size="18"
					fill="var(--g-on-brand)"
				>n</text>
			</svg>
			<span
				v-show="!collapsed"
				class="font-extrabold text-button-label tracking-tight whitespace-nowrap text-inkbase"
			>
				{{ __("Nadi") }}
			</span>
		</div>

		<!-- Nav -->
		<div class="flex flex-col py-3.5 flex-1">
			<button
				type="button"
				class="g-eyebrow flex items-center gap-3 px-[18px] py-3 mb-1.5 border-l-[3px] border-transparent text-ink-500 hover:text-inkbase text-left"
				:aria-label="collapsed ? __('Expand sidebar') : __('Collapse sidebar')"
				:aria-expanded="String(!collapsed)"
				@click="toggleCollapse"
			>
				<svg
					width="17"
					height="17"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.7"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="flex-none transition-transform duration-200"
					:style="{ transform: collapsed ? 'rotate(180deg)' : 'none' }"
				>
					<polyline points="11 17 6 12 11 7" />
					<polyline points="18 17 13 12 18 7" />
				</svg>
				<span v-show="!collapsed" class="whitespace-nowrap">{{ __("Collapse") }}</span>
			</button>

			<router-link
				v-for="item in directItems"
				:key="item.route"
				:to="item.route"
				custom
				v-slot="{ navigate }"
			>
				<button
					type="button"
					class="g-sidenav__item g-focusable"
					:class="{ 'g-sidenav__item--active': isActive(item.route) }"
					@click="navigate"
				>
					<component :is="item.icon" class="h-[17px] w-[17px] flex-none" />
					<span v-show="!collapsed" class="whitespace-nowrap">{{ item.title }}</span>
				</button>
			</router-link>

			<!-- §20.2: below a divider, the contents of More as a FLAT list. More
			     is a container, not a destination — at lg: it dissolves. No
			     nested menus. -->
			<hr class="g-sidenav__divider" />

			<router-link
				v-for="item in moreItems"
				:key="item.route"
				:to="item.route"
				custom
				v-slot="{ navigate }"
			>
				<button
					type="button"
					class="g-sidenav__item g-focusable"
					:class="{ 'g-sidenav__item--active': isActive(item.route) }"
					@click="navigate"
				>
					<component :is="item.icon" class="h-[17px] w-[17px] flex-none" />
					<span v-show="!collapsed" class="whitespace-nowrap">{{ item.title }}</span>
				</button>
			</router-link>
		</div>

		<!-- Profile -->
		<router-link
			:to="{ name: 'Profile' }"
			class="flex items-center gap-2.5 px-[18px] py-4 border-t-2 border-divider hover:bg-inkbase/[0.05]"
		>
			<img
				v-if="employeeImage"
				:src="employeeImage"
				:alt="employeeName"
				class="w-[34px] h-[34px] object-cover flex-none grayscale"
			/>
			<div
				v-else
				class="w-[34px] h-[34px] flex-none grayscale bg-surface flex items-center justify-center font-extrabold text-inkbase"
			>
				{{ employeeName ? employeeName[0] : "?" }}
			</div>
			<div v-show="!collapsed" class="flex flex-col gap-px min-w-0">
				<span class="font-extrabold text-card-title whitespace-nowrap truncate text-inkbase">
					{{ employeeName }}
				</span>
				<span
					class="g-eyebrow whitespace-nowrap truncate"
				>
					{{ employeeDesignation }}
				</span>
			</div>
		</router-link>
	</aside>
</template>

<script setup>
import { ref, computed, inject } from "vue"
import { useRoute } from "vue-router"

import { markRaw } from "vue"

import { TAB_ITEMS, MORE_ITEMS } from "@/data/navItems"
import { hasTeam } from "@/data/team"
import TeamIcon from "@/components/icons/TeamIcon.vue"

const __ = inject("$translate")
const user = inject("$user")
const employee = inject("$employee")

const route = useRoute()

const STORAGE_KEY = "hrms:sidenav-collapsed"
const collapsed = ref(localStorage.getItem(STORAGE_KEY) === "true")

const toggleCollapse = () => {
	collapsed.value = !collapsed.value
	localStorage.setItem(STORAGE_KEY, String(collapsed.value))
}

// Team was reachable ONLY through the phone More menu — a manager on desktop
// had no path to their own team page at all (true on v15 live as well; this
// closes it for both). Same gate More.vue uses: the entry appears once
// has_team confirms direct reports, or the caller is HR browsing via the
// selector. hasTeam auto-fetches and is cached, so this costs nothing extra.
// §20.2: four direct destinations above the divider — TAB_ITEMS without the
// More container, which has no meaning at lg:.
const directItems = computed(() =>
	TAB_ITEMS.filter((item) => item.route !== "/more").map((item) => ({
		...item,
		title: __(item.title),
	}))
)

// …and everything More holds, flat, below it. Team appears only once has_team
// confirms direct reports (or the caller is HR browsing via the selector).
const moreItems = computed(() => [
	...MORE_ITEMS.map((item) => ({ ...item, title: __(item.title) })),
	...(hasTeam.data ? [{ icon: markRaw(TeamIcon), title: __("Team"), route: "/team" }] : []),
])

const isActive = (path) => route.path === path

const employeeImage = computed(() => user?.data?.user_image || "")
const employeeName = computed(() => employee?.data?.employee_name || "")
const employeeDesignation = computed(() => employee?.data?.designation || "")
</script>
