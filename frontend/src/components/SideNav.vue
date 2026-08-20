<template>
	<aside
		class="hidden lg:flex flex-col flex-none border-r-2 border-divider overflow-hidden bg-ground transition-[width] duration-200"
		:style="{ width: collapsed ? '72px' : '216px' }"
	>
		<!-- Logo header (64px) -->
		<div class="h-16 flex items-center gap-2.5 px-4 border-b-2 border-divider flex-none">
			<svg width="32" height="32" viewBox="0 0 117 117" fill="none" class="flex-none">
				<path
					d="M93.4394 0H23.5606C10.5485 0 0 10.5485 0 23.5606V93.4394C0 106.452 10.5485 117 23.5606 117H93.4394C106.452 117 117 106.452 117 93.4394V23.5606C117 10.5485 106.452 0 93.4394 0Z"
					fill="#A1EEC9"
				/>
				<path
					d="M56.3316 68.0044C45.408 68.0044 36.4657 59.1156 36.4657 48.1385V46.425L47.068 46.5321L46.9609 48.1385C46.9609 53.279 51.1376 57.5092 56.3316 57.5092H60.6154C65.7559 57.5092 69.9861 53.3325 69.9861 48.1385V43.8547C69.9861 38.7142 65.8094 34.484 60.6154 34.484H36.3586L36.4657 23.8817L60.6154 23.9888C71.5389 23.9888 80.4813 32.8776 80.4813 43.8547V48.1385C80.4813 59.062 71.5925 68.0044 60.6154 68.0044H56.3316Z"
					fill="#0B313A"
				/>
				<path
					d="M32.1281 85.0856C39.4105 78.7135 48.7812 75.1258 58.5267 75.1258C68.2723 75.1258 77.643 78.7135 84.9254 85.2462L77.8572 93.0105C72.5025 88.2448 65.6485 85.621 58.5267 85.621C51.405 85.621 44.4974 88.2448 39.1428 93.064L32.1817 85.0856H32.1281Z"
					fill="#0B313A"
				/>
			</svg>
			<span
				v-show="!collapsed"
				class="font-extrabold text-button-label tracking-tight whitespace-nowrap text-inkbase"
			>
				{{ __("Frappe HR") }}
			</span>
		</div>

		<!-- Nav -->
		<div class="flex flex-col py-3.5 flex-1">
			<button
				type="button"
				class="flex items-center gap-3 px-[18px] py-3 mb-1.5 border-l-[3px] border-transparent text-kra-label font-extrabold uppercase text-ink-500 hover:text-inkbase text-left"
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
				v-for="item in navItems"
				:key="item.route"
				:to="item.route"
				custom
				v-slot="{ navigate }"
			>
				<button
					type="button"
					class="flex items-center gap-3 px-[18px] py-3 border-l-[3px] text-kra-label font-extrabold uppercase text-left"
					:class="
						isActive(item.route)
							? 'border-accent bg-inkbase/[0.06] text-inkbase'
							: 'border-transparent text-ink-600 hover:bg-inkbase/[0.05]'
					"
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
					class="text-micro-label uppercase text-ink-600 whitespace-nowrap truncate"
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

import { NAV_ITEMS } from "@/data/navItems"
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
const navItems = computed(() => [
	...NAV_ITEMS.map((item) => ({ ...item, title: __(item.title) })),
	...(hasTeam.data ? [{ icon: markRaw(TeamIcon), title: __("Team"), route: "/team" }] : []),
])

const isActive = (path) => route.path === path

const employeeImage = computed(() => user?.data?.user_image || "")
const employeeName = computed(() => employee?.data?.employee_name || "")
const employeeDesignation = computed(() => employee?.data?.designation || "")
</script>
