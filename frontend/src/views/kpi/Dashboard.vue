<template>
	<BaseLayout :pageTitle="__('My KPI')">
		<template #body>
			<div class="flex flex-col w-full max-w-2xl mx-auto px-4 py-7 gap-8">
				<template v-if="current">
					<!-- Hero: overall score -->
					<div>
						<div class="m-kicker">
							{{ __("Appraisal cycle") }} · {{ current.cycle }}
						</div>
						<div
							class="flex items-center justify-between mt-3 border-t-2 border-divider pt-4"
						>
							<div class="flex flex-col gap-2">
								<div class="font-sans font-extrabold text-[44px] leading-none tabular-nums">
									{{ formatScore(current.total_score) }}<span
										class="text-[15px] text-ink-500 font-normal"
									>
										/ 100</span>
								</div>
								<div class="flex items-center gap-2.5">
									<span v-if="current.grade" class="m-chip m-chip-solid">
										{{ current.grade }}
									</span>
									<span
										v-if="delta !== null"
										class="text-xs font-sans font-extrabold text-ink-700"
									>
										{{ delta >= 0 ? "+" : "−" }}{{ Math.abs(delta).toFixed(1) }}
										{{ __("vs last cycle") }}
									</span>
								</div>
							</div>
							<svg width="84" height="84" viewBox="0 0 84 84">
								<circle
									cx="42"
									cy="42"
									r="34"
									fill="none"
									stroke="currentColor"
									class="text-ink-300"
									stroke-width="7"
								/>
								<circle
									cx="42"
									cy="42"
									r="34"
									fill="none"
									stroke="currentColor"
									class="text-accent"
									stroke-width="7"
									:stroke-dasharray="`${ringDash} 213.6`"
									transform="rotate(-90 42 42)"
								/>
								<text
									x="42"
									y="47"
									text-anchor="middle"
									fill="currentColor" class="text-inkbase"
									font-size="15"
									font-weight="800"
								>
									{{ formatScore(current.total_score) }}
								</text>
							</svg>
						</div>
					</div>

					<!-- KRA list -->
					<div>
						<div
							class="text-[11px] tracking-[0.08em] uppercase font-sans font-extrabold text-ink-600 mb-2.5"
						>
							{{ __("My KRAs") }}
						</div>
						<div class="border-t-2 border-divider">
							<div
								v-for="(row, idx) in current.kras"
								:key="idx"
								class="m-row flex flex-col gap-1.5 py-3"
							>
								<div class="flex items-center justify-between gap-2">
									<span class="font-sans font-semibold text-[15px]">
										{{ row.kra }}
									</span>
									<span
										v-if="row.per_weightage"
										class="m-chip m-chip-muted whitespace-nowrap"
									>
										{{ formatScore(row.per_weightage) }}%
									</span>
								</div>
								<span v-if="row.kpi" class="text-xs text-ink-600 leading-4">
									{{ row.kpi }}
								</span>
								<div class="flex items-center gap-2.5">
									<div class="m-bar flex-1">
										<div
											class="h-full bg-accent"
											:style="{ width: `${Math.min(barValue(row), 100)}%` }"
										/>
									</div>
									<span
										class="font-sans font-extrabold text-[11px] tabular-nums w-12 text-right"
									>
										{{ formatScore(barValue(row)) }}%
									</span>
								</div>
								<div class="flex flex-wrap gap-x-3 text-[11px] text-ink-500">
									<span v-if="row.target">
										{{ __("Target") }} {{ row.target }}
									</span>
									<span v-if="row.actual">{{ __("Actual") }} {{ row.actual }}</span>
									<span v-if="row.weighted_score">
										{{ __("Weighted") }} {{ formatScore(row.weighted_score) }}
									</span>
								</div>
							</div>
							<EmptyState
								v-if="!current.kras.length"
								:message="__('No KRAs in this appraisal')"
							/>
						</div>
					</div>

					<!-- Score trend -->
					<div v-if="trend.length > 1">
						<div
							class="text-[11px] tracking-[0.08em] uppercase font-sans font-extrabold text-ink-600 mb-2.5"
						>
							{{ __("Score trend") }}
						</div>
						<div class="border-t-2 border-divider pt-3">
							<svg :viewBox="`0 0 320 110`" class="w-full">
								<line
									v-for="g in [0, 50, 100]"
									:key="g"
									:y1="trendY(g)"
									:y2="trendY(g)"
									x1="24"
									x2="312"
									stroke="currentColor"
									class="text-ink-300"
									stroke-width="1"
								/>
								<text
									v-for="g in [0, 50, 100]"
									:key="'l' + g"
									x="20"
									:y="trendY(g) + 3"
									text-anchor="end"
									fill="currentColor" class="text-ink-500"
									font-size="9"
								>
									{{ g }}
								</text>
								<polyline
									fill="none"
									stroke="currentColor"
									class="text-inkbase"
									stroke-width="2"
									:points="trendPoints"
								/>
								<g v-for="(p, i) in trend" :key="'p' + i">
									<circle :cx="trendX(i)" :cy="trendY(p.total_score)" r="3" fill="currentColor" class="text-inkbase" />
									<text
										:x="trendX(i)"
										y="106"
										text-anchor="middle"
										fill="currentColor" class="text-ink-500"
										font-size="9"
									>
										{{ p.cycle }}
									</text>
								</g>
							</svg>
						</div>
					</div>

					<!-- Feedback -->
					<div>
						<div class="border-t-2 border-divider">
							<div class="m-row flex items-center justify-between py-3">
								<span class="text-sm">
									{{ __("Feedback received this cycle") }}
								</span>
								<span class="font-sans font-extrabold text-base tabular-nums">
									{{ dashboard.data.feedback.count }}
								</span>
							</div>
						</div>
						<span class="block text-[11px] text-ink-600 mt-3">
							🔒 {{ __("You can only see your own scores") }}
						</span>
					</div>
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
