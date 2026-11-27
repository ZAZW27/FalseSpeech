<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { API_BASE } from '@/assets/js/api'
import { formatDateTime, formatSessionDuration, ratioToPercent } from '@/assets/js/format'
import { getVerdictMeta } from '@/assets/js/historyStats'
import Icon from '@/components/ui/icons/Icon.vue'
import StatusChip from '@/components/ui/badges/StatusChip.vue'
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'
import SessionRiskTimeline from '@/components/history/SessionRiskTimeline.vue'

const route = useRoute()

const report = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')
const selectedChunkBySession = ref({})
const copiedHash = ref(false)

const sessionList = computed(() => {
  if (!report.value) return []
  if (Array.isArray(report.value.sessions) && report.value.sessions.length) return report.value.sessions
  return [report.value]
})

const toggleChunk = (sid, key) => {
  const cur = selectedChunkBySession.value[sid]
  selectedChunkBySession.value = { ...selectedChunkBySession.value, [sid]: cur === key ? null : key }
}

const formatChunkTime = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const copyDigest = async () => {
  if (!report.value?.integrity_hash) return
  try {
    await navigator.clipboard.writeText(report.value.integrity_hash)
    copiedHash.value = true
    setTimeout(() => {
      copiedHash.value = false
    }, 2000)
  } catch {}
}

const printReport = () => {
  window.print()
}

const loadReport = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const token = encodeURIComponent(String(route.params.token || ''))
    const res = await fetch(`${API_BASE}/api/verify/${token}`)
    if (!res.ok) {
      let detail = 'Verification link is invalid or has expired.'
      try {
        const body = await res.json()
        if (body?.detail) detail = body.detail
      } catch {}
      throw new Error(detail)
    }
    report.value = await res.json()
  } catch (err) {
    errorMessage.value = err?.message || 'Could not verify this report.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadReport)
</script>

<template>
  <div class="min-h-screen bg-back-prime px-4 py-8 text-slate-100 sm:px-6 lg:px-8">
    <div class="mx-auto flex max-w-4xl flex-col gap-5">
      <!-- Top Brand Bar -->
      <header class="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
        <RouterLink to="/" class="flex items-center gap-2.5 text-lg font-bold text-slate-100">
          <Icon name="logo" :size="28" />
          <span>False Speech</span>
        </RouterLink>

        <div class="flex items-center gap-2.5">
          <span class="rounded-full border-2 border-brand-green/50 bg-[#2f6b5e]/80 px-3 py-1 text-[11px] font-bold text-slate-100">
            Verified Read-Only Report
          </span>
          <button
            v-if="report"
            type="button"
            class="rounded-xl border border-white/15 bg-white/5 px-3.5 py-1.5 text-xs font-semibold text-slate-100 transition hover:bg-white/15 print:hidden"
            @click="printReport"
          >
            Print / Save PDF
          </button>
        </div>
      </header>

      <!-- Loading -->
      <div v-if="isLoading" class="flex flex-col gap-4">
        <div class="skeleton-shimmer h-36 rounded-3xl" />
        <div class="skeleton-shimmer h-40 rounded-3xl" />
        <div class="skeleton-shimmer h-56 rounded-3xl" />
      </div>

      <!-- Error / Invalid Token -->
      <div
        v-else-if="errorMessage"
        class="rounded-3xl border-2 border-red-400/30 bg-red-400/10 p-10 text-center"
        role="alert"
      >
        <h1 class="text-xl font-bold text-slate-100">Report Verification Failed</h1>
        <p class="mt-2 text-sm text-red-300">{{ errorMessage }}</p>
        <RouterLink
          to="/"
          class="mt-6 inline-flex rounded-xl border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold text-slate-100 transition hover:bg-white/15"
        >
          Back to False Speech
        </RouterLink>
      </div>

      <!-- Verified Report Certificate (supports both single session and multi-session bundles) -->
      <template v-else-if="report">
        <div
          v-if="sessionList.length > 1"
          class="rounded-2xl border-2 border-back-secondary bg-back-secondary/40 px-5 py-4 text-xs text-slate-300"
        >
          <p class="text-sm font-bold text-slate-100">
            Verified Multi-Session Screening Bundle ({{ sessionList.length }} Sessions)
          </p>
          <p class="mt-0.5 text-slate-400">
            Prepared by <strong class="text-slate-200">{{ report.reviewed_by }}</strong>. Every session below is cryptographically verified.
          </p>
        </div>

        <div v-for="entry in sessionList" :key="entry.session_id" class="flex flex-col gap-5">
          <!-- Session Summary Card -->
          <section class="rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-6">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Voice Authenticity Verification Certificate
                </p>
                <h1 class="mt-1 text-2xl font-extrabold text-slate-100">
                  {{ entry.title }}
                  <span class="ml-1.5 text-sm font-semibold text-slate-400">#{{ entry.session_id }}</span>
                </h1>
                <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                  <span>Screened: <strong class="text-slate-200">{{ formatDateTime(entry.started_at) }}</strong></span>
                  <span>&bull;</span>
                  <span>Duration: <strong class="tabular-nums text-slate-200">{{ formatSessionDuration(entry.duration) }}</strong></span>
                  <span>&bull;</span>
                  <span>Source: <strong class="uppercase text-slate-200">{{ entry.source }}</strong></span>
                  <span>&bull;</span>
                  <span>Prepared by: <strong class="text-slate-200">{{ entry.reviewed_by }}</strong></span>
                </div>
              </div>

              <div class="flex flex-col items-end gap-2">
                <StatusChip :label="getVerdictMeta(entry.verdict).label" :tone="getVerdictMeta(entry.verdict).tone" />
                <span class="text-xs font-bold tabular-nums text-slate-100">
                  {{ ratioToPercent(entry.fake_ratio) }}% Avg AI Risk ({{ entry.fake_count }} AI / {{ entry.real_count }} Human)
                </span>
              </div>
            </div>

            <p v-if="entry.notes" class="mt-4 rounded-xl border border-white/10 bg-back-prime/60 px-4 py-3 text-xs leading-relaxed text-slate-300">
              <span class="font-semibold text-slate-400">HR Notes:</span> {{ entry.notes }}
            </p>
          </section>

          <!-- HR Risk Brief -->
          <section
            v-if="entry.hr_brief"
            class="rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-6"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">HR Risk Brief</p>
              <span
                :class="[
                  'rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase',
                  entry.hr_brief.risk_level === 'High'
                    ? 'border-red-400/40 text-red-300'
                    : entry.hr_brief.risk_level === 'Moderate'
                      ? 'border-amber-400/40 text-amber-200'
                      : 'border-brand-green/40 text-brand-green',
                ]"
              >
                {{ entry.hr_brief.risk_level }} Risk
              </span>
            </div>
            <h2 class="mt-2 text-base font-bold text-slate-100">{{ entry.hr_brief.headline }}</h2>
            <p class="mt-1.5 text-xs leading-relaxed text-slate-300">{{ entry.hr_brief.summary }}</p>
            <p class="mt-2 text-xs text-slate-200">
              <span class="font-semibold text-slate-400">Recommended Action:</span> {{ entry.hr_brief.recommendation }}
            </p>
          </section>

          <!-- Visual Risk Timeline -->
          <section v-if="entry.segments && entry.segments.length" class="rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-6">
            <SessionRiskTimeline
              class="!mt-0 !border-0 !bg-transparent !p-0"
              :segments="entry.segments"
              :selected-chunk-id="selectedChunkBySession[entry.session_id] ?? null"
              @select-chunk="(k) => toggleChunk(entry.session_id, k)"
            />
          </section>

          <!-- Chunk-by-Chunk Audit Breakdown -->
          <section class="rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-6">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Chunk-by-Chunk Verification Log ({{ entry.segments.length }})
            </p>

            <div class="mt-3 overflow-x-auto rounded-xl border border-white/10 bg-back-prime/70">
              <table class="w-full min-w-[520px] text-left text-xs">
                <thead>
                  <tr class="border-b border-white/10 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                    <th class="px-4 py-2.5">Chunk #</th>
                    <th class="px-4 py-2.5">Time</th>
                    <th class="px-4 py-2.5">Duration</th>
                    <th class="px-4 py-2.5">Fake Probability</th>
                    <th class="px-4 py-2.5">Real Probability</th>
                    <th class="px-4 py-2.5 text-right">Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="seg in entry.segments"
                    :key="seg.id ?? seg.offset"
                    :class="[
                      'border-b border-white/5 transition last:border-b-0 hover:bg-white/[0.04]',
                      selectedChunkBySession[entry.session_id] === (seg.id ?? seg.offset) ? 'bg-white/[0.08]' : '',
                    ]"
                    @click="toggleChunk(entry.session_id, seg.id ?? seg.offset)"
                  >
                    <td class="px-4 py-2.5 tabular-nums text-slate-300">#{{ seg.offset }}</td>
                    <td class="px-4 py-2.5 tabular-nums text-slate-300">{{ formatChunkTime(seg.recorded_at) }}</td>
                    <td class="px-4 py-2.5 tabular-nums text-slate-300">
                      {{ seg.duration_s ? `${Number(seg.duration_s).toFixed(1)}s` : '-' }}
                    </td>
                    <td class="px-4 py-2.5">
                      <div class="flex items-center gap-2.5">
                        <ConfidenceBar
                          :value="ratioToPercent(seg.fake_prob)"
                          :tone="seg.is_fake ? 'danger' : 'success'"
                          height-class="h-1.5"
                          class="w-20"
                        />
                        <span class="font-semibold tabular-nums text-slate-100">{{ ratioToPercent(seg.fake_prob) }}%</span>
                      </div>
                    </td>
                    <td class="px-4 py-2.5 tabular-nums text-slate-300">
                      {{ ratioToPercent(seg.real_prob ?? (1 - seg.fake_prob)) }}%
                    </td>
                    <td class="px-4 py-2.5 text-right">
                      <StatusChip
                        :label="seg.is_fake ? 'AI / Fake' : 'Human'"
                        :tone="seg.is_fake ? 'danger' : 'success'"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tamper-Evident Cryptographic Footer -->
        <footer class="rounded-2xl border-2 border-back-secondary bg-back-prime/80 px-5 py-4 text-xs text-slate-400">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-semibold text-slate-200">Tamper-Evident SHA-256 Integrity Fingerprint</span>
            <button
              type="button"
              class="rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-slate-200 transition hover:bg-white/15 print:hidden"
              @click="copyDigest"
            >
              {{ copiedHash ? 'Copied' : 'Copy Digest' }}
            </button>
          </div>
          <p class="mt-1.5 break-all text-[11px] text-slate-300">{{ report.integrity_hash }}</p>
          <p class="mt-2 text-[11px] text-slate-400">
            This report was cryptographically signed by False Speech. Zero raw audio is stored on disk; only verified inference scores and metadata are retained.
          </p>
        </footer>
      </template>
    </div>
  </div>
</template>
