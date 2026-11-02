export const pricingHeader = {
  eyebrow: 'Subscriptions',
  title: 'Pick the plan that fits how you listen.',
  description:
    'Start free, upgrade when you need more minutes, deeper detail, or the Android widget.',
}

// Used by the Subscription section (list) and the Detail page (/detail/:id).
export const plans = [
  {
    id: 'free',
    name: 'Free',
    price: 'Rp0',
    period: 'forever',
    featured: false,
    tag: null,
    summary: 'A no-cost way to try live voice checking.',
    description:
      'Free gives you ten minutes of live listening every day with a plain TRUE or FALSE answer. It is the quickest way to see how False Speech behaves on your own calls.',
    features: [
      '10 minutes per day',
      'TRUE / FALSE result only',
      'Standard processing queue',
      'Web dashboard',
    ],
    cta: { label: 'Get started', variant: 'outline' },
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 'Rp49.000',
    period: 'per month',
    featured: false,
    tag: null,
    summary: 'More listening time and a confidence score.',
    description:
      'Pro extends listening to five hours per day and adds a confidence score to every verdict. Your audio is processed in the high-priority queue, so answers arrive faster.',
    features: [
      '5 hours per day',
      'Confidence score',
      'High-priority processing',
      'Web dashboard',
    ],
    cta: { label: 'Choose Pro', variant: 'dark' },
  },
  {
    id: 'pro-max',
    name: 'Pro Max',
    price: 'Rp199.000',
    period: 'per month',
    featured: true,
    tag: 'Most popular',
    summary: 'Long sessions, top priority, and the Android widget.',
    description:
      'Pro Max gives you twelve hours of listening per day, the highest processing priority, and an Android app with a home-screen widget. One tap starts a session, one tap stops it.',
    features: [
      '12 hours per day',
      'Confidence score',
      'Highest-priority processing',
      'Android app & home widget',
    ],
    cta: { label: 'Choose Pro Max', variant: 'primary' },
  },
  {
    id: 'lifetime',
    name: 'Lifetime',
    price: 'Rp2.499.000',
    period: 'one-time payment',
    featured: false,
    tag: null,
    summary: 'Pay once and keep every Pro Max feature.',
    description:
      'Lifetime removes the daily limit under a fair-usage policy and includes everything in Pro Max. You pay one time and keep access for good.',
    features: [
      'No daily limit (fair usage)',
      'Everything in Pro Max',
      'Highest-priority processing',
      'Pay once, use for good',
    ],
    cta: { label: 'Get Lifetime', variant: 'dark' },
  },
]

export const getPlanById = (id) => plans.find((plan) => plan.id === id) ?? null
