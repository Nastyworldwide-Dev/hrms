<template>
	<!-- One row of an inset grouped form (alpha.6 B2; Apple HIG Lists and
	     tables): the label leads, the control trails. Long text stacks: its
	     label on top, the text under it, on the same row surface. -->
	<div
		v-if="showField"
		class="g-form-row"
		:class="{ 'g-form-row--stacked': isStacked, 'g-form-row--error': props.errorMessage }"
	>
		<span
			v-if="!['Check', 'Section Break', 'Column Break'].includes(props.fieldtype)"
			class="g-form-row__label"
			:class="{ 'g-form-row__label--required': props.reqd }"
		>
			{{ label }}
		</span>

		<!-- Select, or a Link with a fixed option list (documentList): a native
			 <select> in the Glass skin — the phone's own picker, not frappe-ui's
			 Autocomplete (the grey "Select Leave Type" box). No placeholder
			 words: the label above already names the field. -->
		<GSelect
			v-if="props.fieldtype === 'Select' || props.documentList"
			:options="selectionList"
			:model-value="modelValue"
			:aria-label="label"
			v-bind="$attrs"
			:disabled="isReadOnly"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Link field: Glass searchable picker (input-skinned trigger + sheet) -->
		<Link
			v-else-if="props.fieldtype === 'Link'"
			:doctype="props.options"
			:modelValue="modelValue"
			:filters="props.linkFilters"
			:disabled="isReadOnly"
			:aria-label="label"
			@update:modelValue="(v) => emit('update:modelValue', v)"
		/>

		<!-- Rich text keeps frappe-ui's TextEditor (nothing native does rich
			 text); the Glass container supplies the border, fill and radius. -->
		<div v-else-if="props.fieldtype === 'Text Editor'" class="g-texteditor">
			<TextEditor
				:content="modelValue"
				@change="(v) => emit('update:modelValue', v)"
				:fixedMenu="true"
				:editable="!isReadOnly"
				editor-class="prose-sm p-2 min-h-16"
			/>
		</div>

		<!-- Text -->
		<GTextarea
			v-else-if="['Small Text', 'Text', 'Long Text'].includes(props.fieldtype)"
			:model-value="modelValue"
			:aria-label="label"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<!-- Check: a switch trailing its row (Apple HIG Toggles: in a list row,
		     the row text is the label). The row itself is the 44px target. -->
		<template v-else-if="props.fieldtype === 'Check'">
			<span class="g-form-row__label">{{ label }}</span>
			<GSwitch
				class="g-form-row__switch"
				:aria-label="label"
				:model-value="modelValue"
				v-bind="$attrs"
				:disabled="isReadOnly"
				@update:model-value="(v) => emit('update:modelValue', v)"
				@change="(v) => emit('change', v)"
			/>
		</template>

		<!-- Data field -->
		<GInput
			v-else-if="props.fieldtype === 'Data'"
			:model-value="modelValue"
			:aria-label="label"
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
			:aria-label="label"
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
			:aria-label="label"
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
				{{ label }}
			</h2>
		</div>

		<!-- Date: GDatePicker is a native <input type="date"> in the Glass skin —
			 the phone's own date wheel. min/maxDate forward to min/max, though
			 nothing in this app's backend has ever populated
			 field.minDate/maxDate on any doctype. -->
		<GDatePicker
			v-else-if="props.fieldtype === 'Date'"
			:model-value="modelValue"
			:aria-label="label"
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
			 hardcoded grey border that never adapted to dark mode. -->
		<GInput
			v-else-if="props.fieldtype === 'Time'"
			type="time"
			:aria-label="label"
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

		<!-- Datetime: native datetime-local, converted to Frappe's format -->
		<GDateTimePicker
			v-else-if="props.fieldtype === 'Datetime'"
			:model-value="modelValue"
			:aria-label="label"
			:disabled="isReadOnly"
			v-bind="$attrs"
			@update:model-value="
				(v) => {
					emit('update:modelValue', v)
					emit('change', v)
				}
			"
		/>

		<p v-if="props.errorMessage" class="g-field-error" role="alert">{{ props.errorMessage }}</p>
	</div>
</template>

<script setup>
import GTextarea from "@/components/glass/GTextarea.vue"
import GInput from "@/components/glass/GInput.vue"
import GDatePicker from "@/components/glass/GDatePicker.vue"
import GDateTimePicker from "@/components/glass/GDateTimePicker.vue"
import GSelect from "@/components/glass/GSelect.vue"
import GSwitch from "@/components/glass/GSwitch.vue"
import { TextEditor } from "frappe-ui"
import { sentenceCase } from "@/utils/sentenceCase"
import { plainLabel } from "@/utils/plainLabel"
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

// the doctype label as the server sends it, translated, then sentence case
// ("Leave Type" -> "Leave type"; acronyms like HR/OT/ID stay capital)
// Plain words first (alpha.6 C1: "Leave Type" -> "Kind of leave"), then the
// site's translation, then sentence case.
const label = computed(() => sentenceCase(props.label ? __(plainLabel(props.label)) : ""))

const isLayoutField = computed(() => {
	return ["Section Break", "Column Break"].includes(props.fieldtype)
})

const showField = computed(() => {
	if (
		props.readOnly &&
		!isLayoutField.value &&
		(props.modelValue == null || props.modelValue === "")
	)
		return false

	return props.fieldtype !== "Table" && !props.hidden
})

//: Long text (and rich text) needs the row's full width: label on top.
const isStacked = computed(() =>
	["Small Text", "Text", "Long Text", "Text Editor"].includes(props.fieldtype)
)

const isNumberType = computed(() => {
	return ["Int", "Float", "Currency"].includes(props.fieldtype)
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
	if (props.modelValue != null && props.modelValue !== "") return

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
