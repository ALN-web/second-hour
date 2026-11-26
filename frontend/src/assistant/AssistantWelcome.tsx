interface AssistantWelcomeProps {
  userName?: string
  onSelectPrompt: (promptText: string) => void
}

const STARTER_PROMPTS = [
  {
    id: 'docs',
    title: 'Understand My Documents',
    description: 'Review uploaded medical bills, reports, RC, and driving licence in your wallet.',
    icon: (
      <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    badge: 'Wallet Grounded',
    badgeColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    query: 'Show me all the documents in my Document Wallet and highlight any unverified or expiring items.',
  },
  {
    id: 'vehicle',
    title: 'Check Vehicle Information',
    description: 'Check registration, insurance policy number, and expiry countdowns.',
    icon: (
      <svg className="w-5 h-5 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 19H5a2 2 0 01-2-2V9a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2z" />
        <circle cx="7.5" cy="14.5" r="1.5" />
        <circle cx="16.5" cy="14.5" r="1.5" />
      </svg>
    ),
    badge: 'Vehicle Records',
    badgeColor: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
    query: 'What is the current insurance status of my registered vehicles and how many days are left?',
  },
  {
    id: 'case',
    title: 'Track My Accident Case',
    description: 'Monitor hospital liaison, treating doctor status, police draft, and pending tasks.',
    icon: (
      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    badge: 'Live Case Status',
    badgeColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    query: 'Give me an update on my accident case, hospital treatment, and police report status.',
  },
  {
    id: 'pmrahat',
    title: 'PM-RAHAT Guidance',
    description: 'Learn about ₹1.5L cashless trauma care rules, 7-day cover, and hospital eligibility.',
    icon: (
      <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
    badge: 'Official MoRTH Data',
    badgeColor: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
    query: 'How does PM-RAHAT cashless assistance work, what is the ₹1.5 lakh limit, and who is eligible?',
  },
  {
    id: 'insurance',
    title: 'Insurance Assistance',
    description: 'Understand claim filing steps, surveyor visits, and cashless coordination.',
    icon: (
      <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
    badge: 'Claims Guidance',
    badgeColor: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    query: 'What documents and steps do I need to prepare for my motor insurance claim?',
  },
  {
    id: 'goldenhour',
    title: 'What Should I Do After an Accident?',
    description: 'Immediate golden hour checklist, medical care, and legal protection.',
    icon: (
      <svg className="w-5 h-5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    badge: 'Immediate Action',
    badgeColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    query: 'What are the critical steps to take immediately following a road accident?',
  },
]

export function AssistantWelcome({
  userName = 'Priya',
  onSelectPrompt,
}: AssistantWelcomeProps) {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Emergency Alert Banner */}
      <div className="mb-8 p-3.5 rounded-xl bg-gradient-to-r from-red-950/40 via-red-900/30 to-amber-950/40 border border-red-500/30 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-red-600/30 flex items-center justify-center text-red-400 shrink-0">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p className="text-xs text-red-200">
            <strong className="text-white">Emergency Assistance:</strong> In case of active danger or severe injury, dial <strong className="text-white">112</strong> for immediate police and medical response.
          </p>
        </div>
        <a
          href="tel:112"
          className="shrink-0 px-3 py-1 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition shadow-sm"
        >
          Call 112
        </a>
      </div>

      {/* Main Greeting & Heading */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#122847] border border-[#234575] text-[#ff7518] text-xs font-semibold mb-3">
          <span className="w-2 h-2 rounded-full bg-[#ff7518] animate-pulse" />
          <span>Connected to Second Hour Services</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          How can I help you today, {userName}?
        </h1>
        <p className="text-sm text-slate-300 mt-2 max-w-xl mx-auto leading-relaxed">
          I am your context-aware assistant. Ask about your registered vehicles, insurance expiry, document wallet, active accident cases, or official PM-RAHAT scheme rules.
        </p>
      </div>

      {/* 6 Starter Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {STARTER_PROMPTS.map((card) => (
          <button
            key={card.id}
            onClick={() => onSelectPrompt(card.query)}
            className="group p-4 rounded-2xl bg-[#0c1c33]/90 hover:bg-[#112644] border border-[#1b3457] hover:border-[#ff7518]/60 transition-all duration-200 text-left flex flex-col justify-between hover:shadow-lg hover:shadow-black/20 hover:-translate-y-0.5 cursor-pointer"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 rounded-xl bg-[#071324] border border-[#1b3457] group-hover:border-[#ff7518]/40 transition">
                  {card.icon}
                </div>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${card.badgeColor}`}>
                  {card.badge}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-white group-hover:text-[#ff7518] transition">
                {card.title}
              </h3>
              <p className="text-xs text-slate-400 mt-1.5 line-clamp-2 leading-relaxed">
                {card.description}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-[#162e4f] flex items-center justify-between text-xs text-slate-400 group-hover:text-white transition">
              <span className="text-[11px] font-medium">Ask this query</span>
              <svg className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform text-[#ff7518]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
