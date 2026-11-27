<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

const STORAGE_KEY = 'fs_dashboard_tutorial_seen_v1'

const ALL_STEPS = [
  {
    id: 'welcome',
    target: null,
    title: 'Welcome to False Speech Dashboard',
    body: 'This quick walkthrough explains how to set up your audio input, start live voice screening, read AI detection verdicts, and review your daily activity. You can replay this guide anytime using the Tutorial button in the bottom-right corner.',
  },
  {
    id: 'play-control',
    target: '[data-tour="play-control"]',
    title: 'Start and Stop Listening',
    body: 'Press the Play button to start real-time deepfake voice screening. Watch the volume bar move to confirm audio is coming through. When you stop listening, every chunk recorded during that run is saved together as one session in Detection History.',
  },
  {
    id: 'auto-detect',
    target: '[data-tour="auto-detect"]',
    title: 'Auto-Detect Audio Driver',
    body: 'Not sure which input captures your system audio? Click Auto-Detect to play a short test sound and scan every driver on your computer. Working drivers are marked with a green dot and tagged as Internal (system audio) or External (microphone).',
  },
  {
    id: 'capture-controls',
    target: '[data-tour="capture-controls"]',
    title: 'Capture Mode, Input, and Chunk Size',
    body: 'Use Mode A to capture directly from an internal system loopback or monitor driver, or switch to Mode B to share any browser tab or system audio across Chrome, Brave, Edge, and Firefox. Adjust Chunk Size (1s to 15s) to balance faster updates against longer voice context. Your choices are saved automatically.',
  },
  {
    id: 'verdict-panel',
    target: '[data-tour="verdict-panel"]',
    title: 'Live Detection Verdict',
    body: 'Each analyzed audio chunk updates this panel with a REAL, FAKE, UNCERTAIN, or SILENT verdict along with the AI fake probability score. Use this during live interviews, calls, or media playback to spot synthetic voices immediately.',
  },
  {
    id: 'terminal-toggle',
    target: '[data-tour="terminal-toggle"]',
    title: 'Optional Live Terminal',
    body: 'Click Show Terminal if you want to inspect technical connection logs, chunk sizes, session IDs, and raw scores in real time. Keep it hidden for a cleaner workspace. Your preference is remembered between visits.',
  },
  {
    id: 'stats-row',
    target: '[data-tour="stats-row"]',
    title: 'Daily Quota, Stats, and Session History',
    body: 'Track your daily listening time, total checks, AI voices flagged, and human voices verified here. Scroll down to view your 7-day activity chart and live session table, or open Detection History in the sidebar to inspect chunks, add HR notes, and export reports.',
  },
]

const isOpen = ref(false)
const stepIndex = ref(0)
const activeSteps = ref([])
const spotlightRect = ref(null)
const viewport = ref({ width: 1280, height: 800 })

const currentStep = computed(() => activeSteps.value[stepIndex.value] || null)
const isFirst = computed(() => stepIndex.value === 0)
const isLast = computed(() => stepIndex.value >= activeSteps.value.length - 1)

const updateViewport = () => {
  if (typeof window === 'undefined') return
  viewport.value = { width: window.innerWidth, height: window.innerHeight }
}

const buildAvailableSteps = () => {
  if (typeof document === 'undefined') return ALL_STEPS
  return ALL_STEPS.filter((step) => !step.target || Boolean(document.querySelector(step.target)))
}

const measureCurrentTarget = async (scroll = false) => {
  updateViewport()
  const step = currentStep.value
  if (!step || !step.target) {
    spotlightRect.value = null
    return
  }

  const el = document.querySelector(step.target)
  if (!el) {
    spotlightRect.value = null
    return
  }

  if (scroll) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
    await new Promise((r) => setTimeout(r, 320))
  }

  const r = el.getBoundingClientRect()
  const pad = 8
  spotlightRect.value = {
    top: Math.max(8, r.top - pad),
    left: Math.max(8, r.left - pad),
    width: Math.min(viewport.value.width - 16, r.width + pad * 2),
    height: r.height + pad * 2,
  }
}

const spotlightStyle = computed(() => {
  const r = spotlightRect.value
  if (!r) return null
  return {
    top: `${r.top}px`,
    left: `${r.left}px`,
    width: `${r.width}px`,
    height: `${r.height}px`,
  }
})

const tooltipStyle = computed(() => {
  const vw = viewport.value.width
  const vh = viewport.value.height
  const cardWidth = Math.min(400, vw - 32)
  const r = spotlightRect.value

  // Centered modal card when step has no specific target
  if (!r) {
    return {
      width: `${cardWidth}px`,
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
    }
  }

  const gap = 16
  const estHeight = 250
  const spaceBelow = vh - (r.top + r.height)
  const placeAbove = spaceBelow < estHeight && r.top > estHeight

  let top = placeAbove ? r.top - estHeight - gap : r.top + r.height + gap
  top = Math.max(16, Math.min(vh - estHeight - 16, top))

  let left = r.left + r.width / 2 - cardWidth / 2
  left = Math.max(16, Math.min(vw - cardWidth - 16, left))

  return {
    width: `${cardWidth}px`,
    top: `${top}px`,
    left: `${left}px`,
  }
})

const markSeen = () => {
  try {
    localStorage.setItem(STORAGE_KEY, 'true')
  } catch {}
}

const startTutorial = async () => {
  activeSteps.value = buildAvailableSteps()
  if (!activeSteps.value.length) return
  stepIndex.value = 0
  isOpen.value = true
  await nextTick()
  await measureCurrentTarget(true)
}

const finishTutorial = () => {
  markSeen()
  isOpen.value = false
  spotlightRect.value = null
}

const nextStep = async () => {
  if (isLast.value) {
    finishTutorial()
    return
  }
  stepIndex.value += 1
  await nextTick()
  await measureCurrentTarget(true)
}

const prevStep = async () => {
  if (isFirst.value) return
  stepIndex.value -= 1
  await nextTick()
  await measureCurrentTarget(true)
}

const onKeydown = (e) => {
  if (!isOpen.value) return
  if (e.key === 'Escape') finishTutorial()
  else if (e.key === 'ArrowRight' || e.key === 'Enter') nextStep()
  else if (e.key === 'ArrowLeft') prevStep()
}

const onWindowChange = () => {
  if (isOpen.value) measureCurrentTarget(false)
}

let autoTimer = null

onMounted(() => {
  updateViewport()
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onWindowChange)
  window.addEventListener('scroll', onWindowChange, { passive: true })

  let seen = false
  try {
    seen = localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {}

  if (!seen) {
    autoTimer = setTimeout(() => {
      startTutorial()
    }, 550)
  }
})

onBeforeUnmount(() => {
  if (autoTimer) clearTimeout(autoTimer)
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('resize', onWindowChange)
  window.removeEventListener('scroll', onWindowChange)
})
</script>

<template>
  <!-- Fixed bottom-right floating replay button (Dashboard only) -->
  <button
    type="button"
    class="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-full border-2 border-back-secondary bg-back-prime px-4 py-2.5 text-xs font-bold text-slate-100 shadow-[0_12px_32px_rgba(0,0,0,0.45)] transition hover:border-brand-green/60 hover:text-brand-green"
    aria-label="Open dashboard tutorial"
    @click="startTutorial"
  >
    <span
      class="flex size-5 items-center justify-center rounded-full border border-white/25 bg-white/10 text-[11px] font-extrabold text-slate-100"
      aria-hidden="true"
    >
      ?
    </span>
    <span>Tutorial</span>
  </button>

  <!-- Interactive Spotlight Tutorial Overlay -->
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="isOpen && currentStep"
        class="fixed inset-0 z-[70]"
        role="dialog"
        aria-modal="true"
        :aria-label="currentStep.title"
      >
        <!-- Backdrop when no target element is spotlighted -->
        <div
          v-if="!spotlightStyle"
          class="absolute inset-0 bg-black/70 backdrop-blur-[2px]"
          @click="finishTutorial"
        />

        <!-- Spotlight Cutout Ring around the active dashboard widget -->
        <div
          v-else
          class="pointer-events-none fixed rounded-2xl border-2 border-brand-green/85 transition-all duration-300 ease-out"
          :style="{
            ...spotlightStyle,
            boxShadow: '0 0 0 9999px rgba(10, 14, 22, 0.74), 0 0 28px rgba(183, 216, 148, 0.25)',
          }"
        />

        <!-- Clickable shield outside tooltip so clicks don't accidentally trigger underlying buttons -->
        <div v-if="spotlightStyle" class="absolute inset-0" @click="finishTutorial" />

        <!-- Floating Step Card -->
        <div
          class="fixed z-10 rounded-2xl border-2 border-back-secondary bg-back-prime p-5 text-slate-100 shadow-[0_24px_60px_rgba(0,0,0,0.65)] transition-all duration-300 ease-out"
          :style="tooltipStyle"
          @click.stop
        >
          <div class="flex items-center justify-between gap-3">
            <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Step {{ stepIndex + 1 }} of {{ activeSteps.length }}
            </span>
            <button
              type="button"
              class="text-xs font-semibold text-slate-400 transition hover:text-slate-100"
              @click="finishTutorial"
            >
              Skip
            </button>
          </div>

          <!-- Progress segments -->
          <div class="mt-2.5 flex gap-1.5" aria-hidden="true">
            <span
              v-for="(s, idx) in activeSteps"
              :key="s.id"
              :class="[
                'h-1 flex-1 rounded-full transition-colors duration-300',
                idx <= stepIndex ? 'bg-brand-green' : 'bg-white/15',
              ]"
            />
          </div>

          <h3 class="mt-4 text-base font-bold text-slate-100">{{ currentStep.title }}</h3>
          <p class="mt-2 text-xs leading-relaxed text-slate-300">{{ currentStep.body }}</p>

          <div class="mt-5 flex items-center justify-between gap-2">
            <button
              type="button"
              :disabled="isFirst"
              class="rounded-xl border border-white/15 bg-white/5 px-3.5 py-2 text-xs font-semibold text-slate-200 transition hover:bg-white/15 disabled:opacity-35"
              @click="prevStep"
            >
              Back
            </button>

            <button
              type="button"
              class="rounded-xl bg-gradient-to-r from-[#b7d894] via-[#c3e2a2] to-[#a7cb82] px-4 py-2 text-xs font-bold text-back-prime shadow-sm transition hover:brightness-105"
              @click="nextStep"
            >
              {{ isLast ? 'Finish' : 'Next' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
