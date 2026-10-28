<!--
  HR's manpower board (S4, 22 Oct 2026; mockup tab 6). HR sees a request from the moment it is SENT,
  under "Waiting for manager", and can act on it once the manager approves. Same shape as the HR Issue
  Board: one stat panel, search + department, grouped lists, five rows then See all. The rules live in
  utils/manpowerBoard.js; the server decides who may read (hr_board is HR only, company-fenced).
-->
<template>
	<BaseLayout :pageTitle="__('Manpower requests')">
		<template #body>
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-3.5 w-full max-w-content-column-lg mx-auto px-4 pt-4 pb-8 lg:py-7"
			>
				<span class="g-eyebrow">{{ __("HR · People & Culture") }}</span>

				<!-- ONE surface with dividers (§15.2). Needs HR turns to a danger ink past 30 days and
				     adds a word and a triangle, so the state never rides on colour alone. -->
				<GStatPanel :columns="4" :loading="!board.data && board.loading" :cells="4">
					<GStatTile
						v-for="tile in tiles"
						:key="tile.key"
						:value="tile.value"
						:label="tile.label"
						:class="{ 'mp-hot': tile.hot }"
					/>
				</GStatPanel>
				<p v-if="hot.over" class="mp-hotline" role="status">
					<TriangleAlert class="h-4 w-4 flex-none" aria-hidden="true" />
					<span>{{ hot.word }}</span>
				</p>

				<div class="g-filter-row">
					<GSearchBar
						v-model="search"
						class="flex-1"
						:placeholder="__('Search')"
						:label="__('Search manpower requests')"
					/>
					<GSelect
						:options="departmentOptions"
						:model-value="department"
						:placeholder="__('All departments')"
						:aria-label="__('Department')"
						@update:model-value="(v) => (department = v)"
					/>
				</div>

				<ResourceError :resource="board" :what="__('the manpower requests')" />

				<template v-if="board.data">
					<section v-for="group in groups" :key="group.key" class="flex flex-col gap-2">
						<h2 class="g-eyebrow flex items-center gap-2">
							{{ __(group.title) }}
							<GBadge variant="neutral">{{ group.count }}</GBadge>
						</h2>
						<GListPanel>
							<GListRow
								v-for="row in group.shown"
								:key="row.name"
								:label="rowTitle(row)"
								:sublabel="rowLine(row, { t: __ })"
								:tint="TILE.sop"
								@click="open(row)"
							>
								<template #icon><Users class="g-row-icon" /></template>
								<template #badge>
									<GStatusChip :status="rowChip(row).status" :label="__(rowChip(row).label)" />
								</template>
							</GListRow>
							<GListRow
								v-if="group.more > 0"
								:label="__('See all {0}', [group.count])"
								@click="opened = { ...opened, [group.key]: true }"
							/>
						</GListPanel>
					</section>

					<GEmptyState
						v-if="!groups.length"
						:title="filtered ? __('Nothing matches') : __('No manpower requests yet')"
						:body="
							filtered
								? __('Try a different search or clear the filters.')
								: __('Requests show here the moment a manager sends them.')
						"
					>
						<template v-if="filtered" #action>
							<GButton :label="__('Clear filters')" class="g-btn--compact" @click="clear" />
						</template>
					</GEmptyState>
				</template>
				<GListPanel v-else-if="board.loading" loading :rows="4" />

				<p class="g-form-footer">
					{{ __("HR can act once the manager approves.") }}
				</p>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { TriangleAlert, Users } from "lucide-vue-next"
import { createResource } from "frappe-ui"
import { computed, defineAsyncComponent, inject, ref, watch } from "vue"
import { useRouter } from "vue-router"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"
import GBadge from "@/components/glass/GBadge.vue"
import GButton from "@/components/glass/GButton.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GSearchBar from "@/components/glass/GSearchBar.vue"
import GSelect from "@/components/glass/GSelect.vue"
import GStatPanel from "@/components/glass/GStatPanel.vue"
import GStatTile from "@/components/glass/GStatTile.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { departmentLabel } from "@/utils/departmentLabel"
import { TILE } from "@/utils/iconTile"
import { groupRows, needsHrState, rowChip, rowLine, rowTitle } from "@/utils/manpowerBoard"

const __ = inject("$translate")
const router = useRouter()

const search = ref("")
const department = ref("")
//: the lists the person tapped See all on
const opened = ref({})

//: Loaded on first use, not in the first download.
const GPullRefresh = defineAsyncComponent(() => import("@/components/glass/GPullRefresh.vue"))

// The server fences and counts; search and department narrow the rows AND the numbers, so the tiles
// always add up to the lists under them.
const board = createResource({
	url: "hrms.api.manpower.hr_board",
	makeParams: () => ({
		department: department.value || null,
		search: search.value.trim() || null,
	}),
	auto: true,
})

// A new search or department is a new question to the server, asked once typing settles.
let timer = null
watch([search, department], () => {
	opened.value = {}
	clearTimeout(timer)
	timer = setTimeout(() => board.reload(), 250)
})

async function refresh(event) {
	console.info("[ManpowerHRBoard] pull-to-refresh")
	await Promise.allSettled([board.reload()])
	event.target?.complete?.()
}

const counts = computed(() => board.data?.counts || {})
const hot = computed(() => needsHrState(counts.value, __))
const tiles = computed(() => [
	{ key: "w", label: __("With manager"), value: counts.value.waiting_manager ?? 0 },
	{ key: "n", label: __("Needs HR"), value: counts.value.needs_hr ?? 0, hot: hot.value.over },
	{ key: "r", label: __("Recruiting"), value: counts.value.recruiting ?? 0 },
	{ key: "f", label: __("Filled"), value: counts.value.filled_this_month ?? 0 },
])

const groups = computed(() => groupRows(board.data?.rows, opened.value))
const filtered = computed(() => Boolean(search.value.trim() || department.value))
const departmentOptions = computed(() =>
	(board.data?.departments || []).map((value) => ({ value, label: departmentLabel(value) }))
)
function clear() {
	search.value = ""
	department.value = ""
}
function open(row) {
	console.info("[ManpowerHRBoard] opening", row.name)
	router.push({ name: "ManpowerRequestDetailView", params: { id: row.name } })
}
</script>

<style scoped>
/* the over-30-days tile: the number goes to the danger ink; the word + triangle below carry it too */
.mp-hot :deep(.g-stat__number) {
	color: var(--g-danger-ink);
}
.mp-hotline {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 0;
	font-size: 0.875rem;
	color: var(--g-danger-ink);
}
</style>
