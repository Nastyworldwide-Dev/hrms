<template>
	<BaseLayout :pageTitle="__('My KPI')">
		<template #body>
			<div class="flex flex-col items-center my-7 p-4 gap-5">
				<template v-if="current">
					<!-- Hero: overall score -->
					<div class="flex flex-col w-full bg-white rounded py-5 px-3.5 gap-4">
						<span class="text-gray-600 text-sm font-medium leading-5">
							{{ current.cycle }}
						</span>
						<div class="flex items-center justify-between">
							<div class="flex flex-col gap-1">
								<span class="text-gray-800 text-2xl font-bold leading-7">
									{{ formatScore(current.total_score) }}
									<span class="text-sm text-gray-500 font-medium">/ 100</span>
								</span>
								<span
									v-if="current.grade"
									class="text-gray-700 text-xs font-semibold bg-gray-100 rounded-full px-2 py-0.5 w-fit"
								>
									{{ current.grade }}
								</span>
								<span
									v-if="delta !== null"
									class="text-xs font-semibold"
									:class="delta >= 0 ? 'text-green-700' : 'text-red-700'"
								>
									{{ delta >= 0 ? "↑" : "↓" }} {{ Math.abs(delta).toFixed(1) }}
									{{ __("vs last cycle") }}
								</span>
							</div>
							<svg width="84" height="84" viewBox="0 0 84 84">
								<circle
									cx="42"
									cy="42"
									r="34"
									fill="none"
									stroke="#e5e7eb"
									stroke-width="7"
								/>
								<circle
									cx="42"
									cy="42"
									r="34"
									fill="none"
									stroke="#2a78d6"
									stroke-width="7"
									stroke-linecap="round"
									:stroke-dasharray="`${ringDash} 213.6`"
									transform="rotate(-90 42 42)"
								/>
								<text
									x="42"
									y="47"
									text-anchor="middle"
									class="fill-gray-800 text-sm font-bold"
								>
									{{ formatScore(current.total_score) }}
								</text>
							</svg>
						</div>
					</div>

					<!-- KRA list -->
					<div class="flex flex-col w-full bg-white rounded py-5 px-3.5 gap-4">
						<span class="text-gray-800 text-base font-semibold leading-5">
							{{ __("My KRAs") }}
						</span>
						<div
							v-for="(row, idx) in current.kras"
							:key="idx"
							class="flex flex-col gap-1.5 border-b pb-3 last:border-b-0 last:pb-0"
						>
							<div class="flex items-center justify-between gap-2">
								<span class="text-gray-800 text-sm font-medium leading-5">
									{{ row.kra }}
								</span>
								<span
									v-if="row.per_weightage"
									class="text-gray-500 text-xs font-semibold bg-gray-100 rounded-full px-2 py-0.5 whitespace-nowrap"
								>
									{{ formatScore(row.per_weightage) }}%
								</span>
							</div>
							<span v-if="row.kpi" class="text-gray-600 text-xs leading-4">
								{{ row.kpi }}
							</span>
							<div class="flex items-center gap-2.5">
								<div class="h-1.5 bg-gray-200 rounded-full flex-1 overflow-hidden">
									<div
										class="h-full bg-blue-500 rounded-full"
										:style="{ width: `${Math.min(barValue(row), 100)}%` }"
									/>
								</div>
								<span class="text-gray-700 text-xs font-semibold w-12 text-right">
									{{ formatScore(barValue(row)) }}%
								</span>
							</div>
							<div class="flex gap-3 text-xs text-gray-500">
								<span v-if="row.target">
									{{ __("Target") }}: {{ row.target }}
								</span>
								<span v-if="row.actual">{{ __("Actual") }}: {{ row.actual }}</span>
								<span v-if="row.weighted_score">
									{{ __("Weighted") }}: {{ formatScore(row.weighted_score) }}
								</span>
							</div>
						</div>
						<EmptyState
							v-if="!current.kras.length"
							:message="__('No KRAs in this appraisal')"
						/>
					</div>

					<!-- Score trend -->
					<div
						v-if="trend.length > 1"
						class="flex flex-col w-full bg-white rounded py-5 px-3.5 gap-3"
					>
						<span class="text-gray-800 text-base font-semibold leading-5">
							{{ __("Score trend") }}
						</span>
						<svg :viewBox="`0 0 320 110`" class="w-full">
							<line
								v-for="g in [0, 50, 100]"
								:key="g"
								:y1="trendY(g)"
								:y2="trendY(g)"
								x1="24"
								x2="312"
								stroke="#e5e7eb"
								stroke-width="1"
							/>
							<text
								v-for="g in [0, 50, 100]"
								:key="'l' + g"
								x="20"
								:y="trendY(g) + 3"
								text-anchor="end"
								class="fill-gray-400"
								font-size="9"
							>
								{{ g }}
							</text>
							<polyline
								fill="none"
								stroke="#2a78d6"
								stroke-width="2"
								:points="trendPoints"
							/>
							<g v-for="(p, i) in trend" :key="'p' + i">
								<circle :cx="trendX(i)" :cy="trendY(p.total_score)" r="3" fill="#2a78d6" />
								<text
									:x="trendX(i)"
									y="106"
									text-anchor="middle"
									class="fill-gray-400"
									font-size="9"
								>
									{{ p.cycle }}
								</text>
							</g>
						</svg>
					</div>

					<!-- Feedback -->
					<div class="flex w-full bg-white rounded py-4 px-3.5 items-center justify-between">
						<span class="text-gray-800 text-sm font-medium">
							{{ __("Feedback received this cycle") }}
						</span>
						<span class="text-gray-700 text-sm font-semibold">
							{{ dashboard.data.feedback.count }}
						</span>
					</div>

					<span class="text-gray-500 text-xs leading-4">
						🔒 {{ __("You can only see your own scores") }}
					</span>
				</template>

				<EmptyState
					v-else-if="dashboard.data"
					:message="__('No appraisals found for you yet')"
				/>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject } from "vue"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"

const __ = inject("$translate")

const dashboard = createResource({
	url: "hrms.api.kpi.get_my_kpi_dashboard",
	auto: true,
})

const current = computed(() => dashboard.data?.current)
const trend = computed(() => dashboard.data?.history || [])

const delta = computed(() => {
	const prev = dashboard.data?.previous_score
	if (prev === null || prev === undefined || !current.value) return null
	return current.value.total_score - prev
})

// ring circumference: 2 * PI * 34 ≈ 213.6
const ringDash = computed(() =>
	current.value ? Math.max((current.value.total_score / 100) * 213.6, 0) : 0
)

function formatScore(value) {
	return Number(value || 0).toFixed(1).replace(/\.0$/, "")
}

// KRA rows may be achievement-based (auto) or manager-rated (manual)
function barValue(row) {
	if (row.achievement) return Number(row.achievement)
	if (row.goal_completion) return Number(row.goal_completion)
	if (row.manager_rating) return (Number(row.manager_rating) / 5) * 100
	return 0
}

function trendX(i) {
	const count = Math.max(trend.value.length - 1, 1)
	return 24 + (i * (312 - 24)) / count
}

function trendY(score) {
	// plot area: y 8 (score 100) to y 92 (score 0)
	return 92 - (Math.min(Math.max(score, 0), 100) / 100) * 84
}

const trendPoints = computed(() =>
	trend.value.map((p, i) => `${trendX(i)},${trendY(p.total_score)}`).join(" ")
)
</script>
