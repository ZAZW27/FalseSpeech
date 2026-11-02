// Shared color mapping for verdict tones (used by bars, verdict text, chips).
export const toneStyles = {
  danger: { text: 'text-danger', bar: 'bg-danger' },
  success: { text: 'text-brand-green', bar: 'bg-brand-green' },
  lime: { text: 'text-lime-400', bar: 'bg-lime-400' },
}

export const getTone = (tone) => toneStyles[tone] ?? toneStyles.lime
