<!--
  GRollNumber — a number that rolls to its new value (alpha.13).

  Leave left, overtime hours, the unread count: when the value changes, the
  old one slides up and the new one in from below, as the Clock app's digits
  do (Apple: content replace), instead of jumping. The first value simply
  appears; only a CHANGE rolls. Stopped by the app-wide reduced-motion block.

  Props:
    value  string | number — what to show
-->
<template>
	<span class="g-roll-number">
		<Transition name="g-roll" mode="out-in">
			<span :key="String(value)" class="g-roll-number__value">{{ value }}</span>
		</Transition>
	</span>
</template>

<script setup>
defineProps({
	value: { type: [String, Number], required: true },
})
</script>
