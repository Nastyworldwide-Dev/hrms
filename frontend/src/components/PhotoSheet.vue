<!--
  PhotoSheet — crop and upload a photo (spec §10.3).
  Presented through GModal with a square stage, circle guide, pan/zoom controls.

  Props:
    isOpen    boolean — controlled open state
    file      File — the image file to crop
    saving    boolean — upload in flight: sheet cannot be dismissed, Use photo shows pending
  Emits:
    use(dataUrl) — canvas.toDataURL("image/jpeg", 0.85) of the cropped 512x512 photo
    did-dismiss  — sheet closed without using
    error        — the file could not be decoded as an image
  Slot: title customization (optional)
-->
<template>
	<GModal
		:is-open="isOpen"
		:title="__('Move and zoom')"
		:dismissible="!saving"
		@did-dismiss="$emit('did-dismiss')"
	>
		<!-- Canvas stage with circle guide -->
		<div
			class="photo-stage"
			ref="stageEl"
			tabindex="0"
			@pointerdown="onPointerDown"
			@pointermove="onPointerMove"
			@pointerup="onPointerEnd"
			@pointercancel="onPointerEnd"
			@wheel.prevent="onWheel"
			@keydown="onKeyDown"
			role="application"
			:aria-label="__('Photo crop. Drag to move. Arrow keys move, plus and minus zoom.')"
		>
			<canvas ref="canvas" width="600" height="600" class="photo-canvas" aria-hidden="true" />
			<div class="photo-guide" aria-hidden="true" />
		</div>

		<!-- Zoom controls -->
		<div class="photo-zoom-row">
			<button
				type="button"
				class="ps-icon-btn g-focusable"
				:aria-label="__('Zoom out')"
				:disabled="saving"
				@click="zoomOut"
			>
				<Minus class="h-5 w-5" aria-hidden="true" />
			</button>
			<input
				ref="zoomInput"
				type="range"
				min="1"
				max="4"
				step="0.01"
				:value="zoom"
				:aria-label="__('Zoom')"
				:disabled="saving"
				@input="onZoomInput"
			/>
			<button
				type="button"
				class="ps-icon-btn g-focusable"
				:aria-label="__('Zoom in')"
				:disabled="saving"
				@click="zoomIn"
			>
				<Plus class="h-5 w-5" aria-hidden="true" />
			</button>
		</div>

		<!-- Hint text -->
		<p class="photo-hint">{{ __("Drag to move. Pinch or use the slider to zoom.") }}</p>

		<!-- Action buttons -->
		<div class="photo-btn-row">
			<GButton :label="__('Cancel')" :disabled="saving" @click="$emit('did-dismiss')" />
			<GButton :label="__('Use photo')" :pending="saving" @click="usePhoto" />
		</div>
	</GModal>
</template>

<script setup>
import { ref, watch, inject } from "vue"
import { Minus, Plus } from "lucide-vue-next"
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import { sourceRect, clampOffset } from "@/utils/photoCrop"

const STAGE = 300 // design size; the real stage shrinks with the column, see stageSize()
const stageSize = () => stageEl.value?.clientWidth || STAGE
const STEP = 10
const __ = inject("$translate")

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	file: { type: File, default: null },
	saving: { type: Boolean, default: false },
})

const emit = defineEmits(["use", "did-dismiss", "error"])

const canvas = ref(null)
const zoomInput = ref(null)
const stageEl = ref(null)

// Crop state
const zoom = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)
let img = null
let imgW = 0
let imgH = 0

// Load image when file changes
watch(
	() => props.file,
	(file) => {
		if (!file) return
		const url = URL.createObjectURL(file)
		const newImg = new Image()
		newImg.onload = () => {
			URL.revokeObjectURL(url)
			img = newImg
			imgW = img.width
			imgH = img.height
			zoom.value = 1
			offsetX.value = 0
			offsetY.value = 0
			drawCrop()
		}
		newImg.onerror = () => {
			URL.revokeObjectURL(url)
			emit("error")
		}
		newImg.src = url
	}
)

function drawCrop() {
	const cv = canvas.value
	if (!cv || !img) return

	const ctx = cv.getContext("2d")
	ctx.fillStyle = "#000"
	ctx.fillRect(0, 0, cv.width, cv.height)

	// Get source rect
	const rect = sourceRect({
		imgW,
		imgH,
		stage: stageSize(),
		zoom: zoom.value,
		offsetX: offsetX.value,
		offsetY: offsetY.value,
	})

	ctx.drawImage(img, rect.sx, rect.sy, rect.sSize, rect.sSize, 0, 0, cv.width, cv.height)
}

function setZoom(z) {
	if (!img) return
	zoom.value = Math.min(4, Math.max(1, z))

	// Clamp offsets after zoom change
	const sSize = Math.min(imgW, imgH) / zoom.value
	const { ox, oy } = clampOffset({
		imgW,
		imgH,
		stage: stageSize(),
		sSize,
		offsetX: offsetX.value,
		offsetY: offsetY.value,
	})
	offsetX.value = ox
	offsetY.value = oy

	drawCrop()
}

function zoomIn() {
	setZoom(zoom.value + 0.25)
}

function zoomOut() {
	setZoom(zoom.value - 0.25)
}

function onZoomInput(e) {
	setZoom(parseFloat(e.target.value))
}

function moveBy(dx, dy) {
	if (!img) return
	offsetX.value += dx
	offsetY.value += dy

	// Clamp offsets
	const sSize = Math.min(imgW, imgH) / zoom.value
	const { ox, oy } = clampOffset({
		imgW,
		imgH,
		stage: stageSize(),
		sSize,
		offsetX: offsetX.value,
		offsetY: offsetY.value,
	})
	offsetX.value = ox
	offsetY.value = oy

	drawCrop()
}

// Pointer drag support
const pointers = new Map()
let pinch0 = null

function pdist() {
	const [a, b] = [...pointers.values()]
	return Math.hypot(a.x - b.x, a.y - b.y) || 1
}

function onPointerDown(e) {
	if (props.saving) return
	const cv = stageEl.value
	if (!cv) return
	cv.setPointerCapture(e.pointerId)
	pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
	if (pointers.size === 2) pinch0 = { d: pdist(), z: zoom.value }
}

function onPointerMove(e) {
	if (props.saving) return
	if (!pointers.has(e.pointerId)) return
	const prev = pointers.get(e.pointerId)
	pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })

	if (pointers.size === 2 && pinch0) {
		setZoom((pinch0.z * pdist()) / pinch0.d)
	} else if (pointers.size === 1) {
		moveBy(e.clientX - prev.x, e.clientY - prev.y)
	}
}

function onPointerEnd(e) {
	pointers.delete(e.pointerId)
	pinch0 = null
}

function onWheel(e) {
	if (props.saving) return
	setZoom(zoom.value * (e.deltaY < 0 ? 1.08 : 1 / 1.08))
}

function onKeyDown(e) {
	if (props.saving) return
	if (e.key === "ArrowLeft") {
		moveBy(-STEP, 0)
		e.preventDefault()
	} else if (e.key === "ArrowRight") {
		moveBy(STEP, 0)
		e.preventDefault()
	} else if (e.key === "ArrowUp") {
		moveBy(0, -STEP)
		e.preventDefault()
	} else if (e.key === "ArrowDown") {
		moveBy(0, STEP)
		e.preventDefault()
	} else if (e.key === "+" || e.key === "=") {
		setZoom(zoom.value + 0.1)
		e.preventDefault()
	} else if (e.key === "-" || e.key === "_") {
		setZoom(zoom.value - 0.1)
		e.preventDefault()
	}
}

function usePhoto() {
	if (!img || props.saving) return
	const out = document.createElement("canvas")
	out.width = out.height = 512

	const rect = sourceRect({
		imgW,
		imgH,
		stage: stageSize(),
		zoom: zoom.value,
		offsetX: offsetX.value,
		offsetY: offsetY.value,
	})

	const ctx = out.getContext("2d")
	ctx.drawImage(img, rect.sx, rect.sy, rect.sSize, rect.sSize, 0, 0, 512, 512)

	const dataUrl = out.toDataURL("image/jpeg", 0.85)
	emit("use", dataUrl)
}
</script>

<style scoped>
.photo-stage {
	position: relative;
	width: min(300px, 100%);
	aspect-ratio: 1;
	margin: 4px auto 0;
	border-radius: 14px;
	overflow: hidden;
	background: #000;
	touch-action: none;
	cursor: grab;
	user-select: none;
	-webkit-user-select: none;
}

.photo-stage:active {
	cursor: grabbing;
}

.photo-canvas {
	display: block;
	width: 100%;
	height: 100%;
}

.photo-guide {
	position: absolute;
	inset: 0;
	border-radius: 50%;
	box-shadow: 0 0 0 400px rgba(0, 0, 0, 0.55);
	border: 2px solid rgba(255, 255, 255, 0.92);
	pointer-events: none;
}

.photo-zoom-row {
	display: flex;
	align-items: center;
	gap: 4px;
	padding: 0 8px;
}

.ps-icon-btn {
	flex: none;
	width: 44px;
	height: 44px;
	border: 0;
	border-radius: 22px;
	background: transparent;
	display: grid;
	place-items: center;
	cursor: pointer;
	transition: transform 120ms cubic-bezier(0.2, 0.8, 0.3, 1),
		background 120ms cubic-bezier(0.2, 0.8, 0.3, 1);
	color: var(--g-ink);
}

.ps-icon-btn:active:not(:disabled) {
	transform: scale(0.94);
	background: var(--g-icon-bg);
}

.ps-icon-btn:disabled {
	opacity: 0.4;
	cursor: default;
}

@media (prefers-reduced-motion: reduce) {
	.ps-icon-btn {
		transition: none;
	}
}

.photo-zoom-row input[type="range"] {
	flex: 1;
	min-width: 0;
	min-height: 44px;
	accent-color: var(--g-ink);
	background: transparent;
}

.photo-zoom-row input[type="range"]:focus-visible {
	box-shadow: none;
	outline: 3px solid var(--g-brand);
	outline-offset: -2px;
	border-radius: 12px;
}

.photo-hint {
	margin: 0;
	text-align: center;
	font: 400 0.8125rem/1.125rem var(--g-font-ui);
	color: var(--g-ink2);
}

.photo-btn-row {
	display: flex;
	gap: 12px;
}

.photo-btn-row > * {
	flex: 1;
}
</style>
