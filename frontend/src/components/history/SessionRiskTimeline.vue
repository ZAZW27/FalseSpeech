<script setup>
import { computed, ref } from 'vue'
import { ratioToPercent } from '@/assets/js/format'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  selectedChunkId: { type: [Number, String], default: null },
})

const emit = defineEmits(['select-chunk'])

const hoveredIdx = ref(null)

const points = computed(() => {
  const list = props.segments || []
  const n = list.length
  if (!n) return []

  const w = 640
  const h = 104
  const padX = 18
  const padTop = 14
  const padBottom = 14
  const innerW = w - padX * 2
  const innerH = h - padTop - padBottom

  return list.map((seg, idx) => {
    const pct = ratioToPercent(seg.fake_prob)
    const x = n === 1 ? w / 2 : padX + (idx / (n - 1)) * innerW
    const y = padTop + (1 - pct / 100) * innerH
    return {
      idx,
      key: seg.id ?? seg.offset,
      offset: seg.offset,
      pct,
      isFake: Boolean(seg.is_fake),
      recordedAt: seg.recorded_at,
      durationS: seg.duration_s,
      x,
      y,
      barBottom: padTop + innerH,
      barHeight: Math.max(4, (pct / 100) * innerH),
    }
  })
})

const barWidth = computed(() => {
  const n = points.value.length
  if (n <= 1) return 26
  return Math.max(4, Math.min(22, Math.floor(460 / n)))
})

const polylinePoints = computed(() => points.value.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '))

const areaPath = computed(() => {
  const pts = points.value
  if (pts.length < 2) return ''
  const first = pts[0]
  const last = pts[pts.length - 1]
  const line = pts.map((p) => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
  return `M ${first.x.toFixed(1)} ${first.barBottom} ${line} L ${last.x.toFixed(1)} ${last.barBottom} Z`
})

const activePoint = computed(() => {
  if (hoveredIdx.value !== null && points.value[hoveredIdx.value]) {
    return points.value[hoveredIdx.value]
  }
  if (props.selectedChunkId !== null) {
    const found = points.value.find((p) => p.key === props.selectedChunkId)
    if (found) return found
  }
  return null
})

const peakPoint = computed(() => {
  if (!points.value.length) return null
  return points.value.reduce((best, cur) => (cur.pct > best.pct ? cur : best), points.value[0])
})

const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <div
    v-if="points.length"
    class="mt-3.5 rounded-xl border border-white/10 bg-back-prime/70 p-4"
  >
    <!-- Header & Active Readout -->
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Session Risk Timeline
        </p>
        <p class="mt-0.5 text-xs text-slate-300">
          <template v-if="activePoint">
            <span class="font-bold text-slate-100">Chunk #{{ activePoint.offset }}</span>
            <span v-if="formatTime(activePoint.recordedAt)" class="text-slate-400">
              &bull; {{ formatTime(activePoint.recordedAt) }}
            </span>
            <span class="text-slate-400"> &bull; </span>
            <span :class="activePoint.isFake ? 'font-bold text-red-300' : 'font-bold text-brand-green'">
              {{ activePoint.pct }}% AI Risk ({{ activePoint.isFake ? 'AI / Fake' : 'Human' }})
            </span>
          </template>
          <template v-else-if="peakPoint">
            Peak risk at <span class="font-bold text-slate-100">Chunk #{{ peakPoint.offset }}</span>
            ({{ peakPoint.pct }}%). Hover or click any point to inspect.
          </template>
        </p>
      </div>

      <div class="flex items-center gap-3 text-[11px] text-slate-400">
        <span class="inline-flex items-center gap-1.5">
          <span class="size-2 rounded-full bg-danger" />
          AI Flagged (&ge;50%)
        </span>
        <span class="inline-flex items-center gap-1.5">
          <span class="size-2 rounded-full bg-brand-green" />
          Human (&lt;50%)
        </span>
      </div>
    </div>

    <!-- Interactive SVG Sparkline + Chunk Bars -->
    <div class="mt-3 w-full">
      <svg
        viewBox="0 0 640 104"
        class="h-[104px] w-full overflow-visible"
        role="img"
        aria-label="Session AI risk timeline across chunks"
      >
        <defs>
          <linearGradient id="fs-risk-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#B7D894" stop-opacity="0.22" />
            <stop offset="100%" stop-color="#B7D894" stop-opacity="0.01" />
          </linearGradient>
        </defs>

        <!-- 50% threshold reference line -->
        <line
          x1="14"
          y1="52"
          x2="626"
          y2="52"
          stroke="rgba(255,255,255,0.16)"
          stroke-dasharray="4 4"
          stroke-width="1"
        />
        <text x="624" y="47" text-anchor="end" fill="#94a3b8" font-size="9">50% threshold</text>

        <!-- Baseline -->
        <line x1="14" y1="90" x2="626" y2="90" stroke="rgba(255,255,255,0.08)" stroke-width="1" />

        <!-- Soft area fill under trend line -->
        <path v-if="areaPath" :d="areaPath" fill="url(#fs-risk-area)" />

        <!-- Per-chunk bars -->
        <g v-for="pt in points" :key="`bar-${pt.key}`">
          <rect
            :x="pt.x - barWidth / 2"
            :y="pt.barBottom - pt.barHeight"
            :width="barWidth"
            :height="pt.barHeight"
            rx="3"
            :fill="pt.isFake ? 'rgba(255, 150, 161, 0.45)' : 'rgba(183, 216, 148, 0.35)'"
            :opacity="hoveredIdx === null || hoveredIdx === pt.idx ? 1 : 0.45"
            class="cursor-pointer transition-opacity duration-150"
            @mouseenter="hoveredIdx = pt.idx"
            @mouseleave="hoveredIdx = null"
            @click="$emit('select-chunk', pt.key)"
          />
        </g>

        <!-- Trend polyline -->
        <polyline
          v-if="points.length > 1"
          :points="polylinePoints"
          fill="none"
          stroke="rgba(226, 232, 240, 0.7)"
          stroke-width="1.75"
          stroke-linejoin="round"
          stroke-linecap="round"
          class="pointer-events-none"
        />

        <!-- Interactive nodes -->
        <g v-for="pt in points" :key="`dot-${pt.key}`">
          <circle
            :cx="pt.x"
            :cy="pt.y"
            :r="hoveredIdx === pt.idx || selectedChunkId === pt.key ? 5.5 : 3.5"
            :fill="pt.isFake ? '#ff96a1' : '#B7D894'"
            stroke="#202734"
            stroke-width="1.5"
            class="cursor-pointer transition-all duration-150"
            @mouseenter="hoveredIdx = pt.idx"
            @mouseleave="hoveredIdx = null"
            @click="$emit('select-chunk', pt.key)"
          />
        </g>
      </svg>

      <!-- Axis labels -->
      <div class="mt-1 flex items-center justify-between text-[10px] tabular-nums text-slate-500">
        <span>Chunk #{{ points[0].offset }}</span>
        <span v-if="points.length > 2">Chunk #{{ points[Math.floor(points.length / 2)].offset }}</span>
        <span v-if="points.length > 1">Chunk #{{ points[points.length - 1].offset }}</span>
      </div>
    </div>
  </div>
</template>
