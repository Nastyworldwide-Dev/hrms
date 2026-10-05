<template>
	<div>
		<span class="block text-xs leading-5 text-gray-600">
			{{ props.label }}
		</span>
		<Autocomplete
			ref="autocompleteRef"
			size="sm"
			v-model="value"
			:options="options.data || []"
			:class="disabled ? 'pointer-events-none' : ''"
			:disabled="disabled"
			@update:query="handleQueryUpdate"
		/>
		<span v-if="props.description" class="block text-xs leading-5 text-gray-600 mt-1">
			{{ props.description }}
		</span>
	</div>
</template>

<script setup>
import { createResource, Autocomplete, debounce } from "frappe-ui";
import { ref, computed, watch, onMounted } from "vue";

const props = defineProps({
	doctype: {
		type: String,
		required: true,
	},
	modelValue: {
		type: String,
		required: false,
		default: "",
	},
	filters: {
		type: Object,
		default: {},
	},
	disabled: {
		type: Boolean,
		default: false,
	},
	label: {
		type: String,
		default: "",
	},
	description: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue"]);

const autocompleteRef = ref(null);
// search_link defaults to 10; a roster has more shift types than that
const PAGE_LENGTH = 50;
const searchText = ref("");

const value = computed({
	get: () => props.modelValue,
	set: (val) => {
		if (typeof val === "string") {
			emit("update:modelValue", val);
		} else {
			emit("update:modelValue", val?.value || "");
		}
	},
});

const options = createResource({
	url: "frappe.desk.search.search_link",
	params: {
		doctype: props.doctype,
		txt: searchText.value,
		filters: props.filters,
		page_length: PAGE_LENGTH,
	},
	method: "POST",
	transform: (data) => {
		const mapped = data.map((doc) => {
			let title = null;
			if (doc.label && doc.label !== doc.value) {
				title = doc.label;
			} else if (doc.description) {
				title = doc.description.split(",")[0];
			}
			return {
				label: title ? `${title} : ${doc.value}` : doc.value,
				value: doc.value,
			};
		});
		// the chosen record may sit outside this page: keep it, so the box still names it
		if (props.modelValue && !mapped.find((o) => o.value === props.modelValue)) {
			mapped.unshift({ label: props.modelValue, value: props.modelValue });
		}
		return mapped;
	},
});

const reloadOptions = (searchTextVal) => {
	options.update({
		params: {
			txt: searchTextVal,
			doctype: props.doctype,
			filters: props.filters,
			page_length: PAGE_LENGTH,
		},
	});
	options.reload();
};

const handleQueryUpdate = debounce((newQuery) => {
	const val = newQuery || "";
	if (searchText.value === val) return;
	searchText.value = val;
	reloadOptions(val);
}, 300);

// Open on the FULL list, never on a search for the chosen value: a person on "Security A" saw only the
// shifts with "Security" in the name, and every other shift vanished from the picker (HR, 5 Oct 2026).
// The chosen record is kept in the list by the transform above.
onMounted(() => {
	reloadOptions("");
});

watch(
	() => props.doctype,
	() => {
		if (!props.doctype || props.doctype === options.doctype) return;
		reloadOptions("");
	},
);

watch(
	() => props.filters,
	() => reloadOptions(""),
);
</script>
