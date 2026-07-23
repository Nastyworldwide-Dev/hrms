<template>
	<div class="flex flex-row justify-between items-center pb-2 border-b-2 border-divider">
		<h2 class="m-kicker">
			{{ __("Settle against Advances") }}
		</h2>
	</div>

	<div class="flex flex-col" v-if="expenseClaim.advances?.length">
		<!-- Advance Row -->
		<div
			v-for="advance in expenseClaim.advances"
			:key="advance.name"
			class="flex flex-col py-3 border-b border-divider"
			:class="[
				advance.selected ? 'bg-surface' : '',
				isReadOnly ? '' : 'cursor-pointer',
			]"
			@click="toggleAdvanceSelection(advance)"
		>
			<div class="flex flex-row justify-between items-center px-1">
				<div class="flex flex-row items-start gap-3">
					<FormControl
						type="checkbox"
						class="mt-[0.5px] text-accent"
						v-model="advance.selected"
						:disabled="isReadOnly"
					/>

					<div class="flex flex-col items-start gap-1.5">
						<div class="text-[15px] font-semibold text-inkbase">
							{{ advance.purpose || advance.employee_advance }}
						</div>
						<div class="flex flex-row items-center gap-3 justify-between">
							<div class="text-xs font-normal text-ink-600">
								{{ __("{0}: {1}", [
									__("Unclaimed Amount"),
									formatCurrency(advance.unclaimed_amount, currency),
								]) }}
							</div>
						</div>
					</div>
				</div>

				<div class="flex flex-row items-center gap-2">
					<span class="text-normal text-ink-600">
						{{ currencySymbol }}
					</span>
					<Input
						type="number"
						class="w-20 advance-input"
						v-model="advance.allocated_amount"
						@input="(v) => (advance.selected = v)"
						@click.stop
						:disabled="isReadOnly"
						:max="advance.unclaimed_amount"
						min="0"
					/>
				</div>
			</div>
		</div>
	</div>

	<EmptyState v-else :message="__('No advances found')" :isTableField="true" />
</template>

<script setup>
import { computed, inject } from "vue"
import { getCurrencySymbol } from "@/data/currencies"
import { formatCurrency } from "@/utils/formatters"

const __ = inject("$translate")
const props = defineProps({
	expenseClaim: {
		type: Object,
		required: true,
	},
	currency: {
		type: String,
		required: true,
	},
	isReadOnly: {
		type: Boolean,
		default: false,
	},
})

const currencySymbol = computed(() => getCurrencySymbol(props.currency))

function toggleAdvanceSelection(advance) {
	if (props.isReadOnly) return
	advance.selected = !advance.selected
}
</script>

<style scoped>
.advance-input :deep(input) {
	background-color: var(--color-surface);
	border: 1px solid var(--color-divider);
	border-radius: 0;
	color: var(--color-text);
}
.advance-input :deep(input:focus) {
	border-color: var(--color-accent);
	box-shadow: none;
	outline: none;
}
</style>
