<template>
	<div v-if="showField" class="flex flex-col gap-1.5">
		<!-- Label -->
		<span
			v-if="!['Check', 'Section Break', 'Column Break'].includes(props.fieldtype)"
			:class="[
				// mandatory marker takes the danger ink, not a Tailwind default
				props.reqd ? `after:content-['_*'] after:text-danger-ink` : ``,
				`g-field__label`,
			]"
		>
			{{ props.label }}
		</span>

		<!-- Select or Link field with predefined options.
			 Wrapped in .g-linkfield rather than swapped for GLinkPicker: the
			 wrapper is what carries the glass skin (frappe-ui's Autocomplete
			 hardcodes a 28px trigger — see the CSS), and wrapping leaves the
			 v?.value unwrapping and Link.vue's remote-search binding exactly
			 as they were. GLinkPicker gets the same class, so adopting it
			 later is a drop-in rather than a re-style. -->
		<div v-if="props.fieldtype === 'Select' || props.documentList" class="g-linkfield">
			<Autocomplete
				:class="isReadOnly ? 'pointer-events-none' : ''"
				:placeholder="__('Select {0}', [props.label])"
				:options="selectionList"
				:modelValue="modelValue"
				v-bind="$attrs"
				:disabled="isReadOnly"
				@update:modelValue="(v) => emit('update:modelValue', v?.value)"
			/>
		</div>

		<!-- Link field -->
		<div v-else-if="props.fieldtype === 'Link'" class="g-linkfield">
			<Link
				:doctype="props.options"
				:modelValue="modelValue"
				:filters="props.linkFilters"
				:disabled="isReadOnly"
				@update:modelValue="(v) => emit('update:modelValue', v)"
			/>
		</div>

		<TextEditor
			v-else-if="props.fieldtype === 'Text Editor'"
			:content="modelValue"
			:placeholder="__('Enter {0}', [props.label])"
			@change="(v) => emit('update:modelValue', v)"
			:fixedMenu="true"
			:editable="!isReadOnly"
			editor-class="prose-sm border-b border-x border-gray-200 rounded-b-sm p-1 min-h-[4rem]"
		/>

		<!-- Text -->
		<GTextarea
			v-else-if="['Small Text', 'Text', 'Long Text'].includes(props.fieldtype)"
			:model-value="modelValue"
			:placeholder="__('Enter {0}', [props.label])"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Check. g-checkfield expands the 16x16 box to a §14.1 target without
		     resizing the tick itself — frappe-ui renders a 16px input and does
		     not forward a class to it, so the theme reaches it by descendant. -->
		<div v-else-if="props.fieldtype === 'Check'" class="g-checkfield">
			<Input
				type="checkbox"
				:label="props.label"
				:value="modelValue"
				@input="(v) => emit('update:modelValue', v)"
				@change="(v) => emit('change', v)"
				v-bind="$attrs"
				:disabled="isReadOnly"
				class="text-accent-ink"
			/>
		</div>

		<!-- Data field -->
		<GInput
			v-else-if="props.fieldtype === 'Data'"
			:model-value="modelValue"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Read only currency field -->
		<GInput
			v-else-if="props.fieldtype === 'Currency' && isReadOnly"
			type="text"
			:model-value="modelValue"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Float/Int field -->
		<GInput
			v-else-if="isNumberType"
			type="number"
			:model-value="modelValue"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Section Break -->
		<div
			v-else-if="props.fieldtype === 'Section Break'"
			:class="props.addSectionPadding ? 'mt-2' : ''"
		>
			<hr v-if="props.addSectionPadding" class="h-px border-0 bg-hair mb-3" />
			<h2 v-if="props.label" class="g-eyebrow">
				{{ props.label }}
			</h2>
		</div>

		<!-- Date. Was a raw native <input type="date">, flagged FIXME "poor UI"
			 by whoever wrote it — GDatePicker already existed (skins frappe-ui's
			 real DatePicker popover) but had never been wired into a live form,
			 only the design specimen page. min/maxDate are forwarded for parity
			 with the old input's :min/:max, though nothing in this app's backend
			 has ever populated field.minDate/maxDate on any doctype. -->
		<GDatePicker
			v-else-if="props.fieldtype === 'Date'"
			:model-value="modelValue"
			:placeholder="__('Select {0}', [props.label])"
			:disabled="isReadOnly"
			:min-date="props.minDate"
			:max-date="props.maxDate"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Time: a native input, not a hand-rolled picker — the browser's own
			 time UI is the proven, accessible choice here (frappe-ui ships no
			 time-only widget). Routed through GInput so it gets the same glass
			 token styling as every other field, replacing the hardcoded
			 `border-gray-400` that never adapted to dark mode. -->
		<GInput
			v-else-if="props.fieldtype === 'Time'"
			type="time"
			:aria-label="props.label"
			:model-value="modelValue"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Datetime -->
		<GDateTimePicker
			v-else-if="props.fieldtype === 'Datetime'"
			:model-value="modelValue"
			:placeholder="__('Select {0}', [props.label])"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<ErrorMessage :message="props.errorMessage" />
	</div>
</template>

<script setup>
import GTextarea from "@/components/glass/GTextarea.vue"
import GInput from "@/components/glass/GInput.vue"
import GDatePicker from "@/components/glass/GDatePicker.vue"
import GDateTimePicker from "@/components/glass/GDateTimePicker.vue"
import { Autocomplete, ErrorMessage, Input, TextEditor } from "frappe-ui"
import { computed, onMounted, inject } from "vue"

import Link from "@/components/Link.vue"

const __ = inject("$translate")

const props = defineProps({
	fieldtype: String,
	fieldname: String,
	modelValue: [String, Number, Boolean, Array, Object],
	default: [String, Number, Boolean, Array, Object],
	label: String,
	options: [String, Array],
	linkFilters: Object,
	documentList: Array,
	readOnly: [Boolean, Number],
	reqd: [Boolean, Number],
	hidden: {
		type: [Boolean, Number],
		default: false,
	},
	errorMessage: String,
	minDate: String,
	maxDate: String,
	addSectionPadding: {
		type: Boolean,
		default: true,
	},
})

const emit = defineEmits(["change", "update:modelValue"])
const dayjs = inject("$dayjs")

const showField = computed(() => {
	if (props.readOnly && !isLayoutField.value && !props.modelValue) return false

	return props.fieldtype !== "Table" && !props.hidden
})

const isNumberType = computed(() => {
	return ["Int", "Float", "Currency"].includes(props.fieldtype)
})

const isLayoutField = computed(() => {
	return ["Section Break", "Column Break"].includes(props.fieldtype)
})

const isReadOnly = computed(() => {
	return Boolean(props.readOnly)
})

const selectionList = computed(() => {
	if (props.fieldtype === "Link" && props.documentList) {
		return props.documentList
	} else if (props.fieldtype == "Select" && props.options) {
		const options = props.options.split("\n")
		return options.map((option) => ({
			label: __(option),
			value: option,
		}))
	}

	return []
})

function setDefaultValue() {
	// set default values
	if (props.modelValue) return

	if (props.default) {
		if (props.fieldtype === "Check") {
			emit("update:modelValue", props.default === "1" ? true : false)
		} else if (props.fieldtype === "Date" && props.default === "Today") {
			emit("update:modelValue", dayjs().format("YYYY-MM-DD"))
		} else if (isNumberType.value) {
			emit("update:modelValue", parseFloat(props.default || 0))
		} else {
			emit("update:modelValue", props.default)
		}
	} else {
		props.fieldtype === "Check" ? emit("update:modelValue", false) : emit("update:modelValue", "")
	}
}

onMounted(() => {
	setDefaultValue()
})
</script>
