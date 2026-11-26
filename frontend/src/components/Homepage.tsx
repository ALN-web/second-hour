import { useState } from 'react'
import { SirenIcon, ArrowRightIcon, InfoIcon, ShieldLogo } from './Icons'
import { HeroIllustration } from './HeroIllustration'
import { ProfileReadinessCard } from './ProfileReadinessCard'
import { FeatureCards } from './FeatureCards'
import { InfoStrip } from './InfoStrip'
import { api, setUser } from '../api'

interface HomepageProps {
  user: { user_id: string; name: string; role_label: string } | null
  onReportAccident: () => void
  onOpenVehicles: () => void
  onOpenDocuments: () => void
  onOpenCases: () => void
  onOpenAI: () => void
  onOpenProfile: () => void
  onDemoStaged?: (user: any) => void
}

const STATS = [
  { big: '₹1.5 lakh', label: 'cashless cover per victim', src: 'PIB, 11 Mar 2026' },
  { big: '7 days', label: 'from the accident, maximum', src: 'PIB, 11 Mar 2026' },
  { big: '3,674', label: 'victims discharged without timely police authentication', src: 'PIB, 12 Aug 2026' },
]

export function Homepage({
  user,
  onReportAccident,
  onOpenVehicles,
  onOpenDocuments,
  onOpenCases,
  onOpenAI,
  onOpenProfile,
  onDemoStaged,
}: HomepageProps) {
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')

  const scrollToLearnMore = () => {
    const el = document.getElementById('info-strip-section')
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const stage = async (fresh: boolean) => {
    setBusy(fresh ? 'fresh' : 'stage')
    setErr('')
    try {
      await api(`/api/demo/stage${fresh ? '?fresh=true' : ''}`, { method: 'POST' })
      const us = await api<any[]>('/api/users')
      const priya = us.find(u => u.user_id === 'u_priya')
      if (priya) {
        setUser(priya.user_id)
        onDemoStaged?.(priya)
      }
    } catch (e: any) {
      setErr(e.message)
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* ------------------------------------------------------------- Hero Section */}
      <section className="relative bg-gradient-to-b from-navy-950 via-navy-950 to-navy-900 text-white overflow-hidden pb-20 pt-6 sm:pt-10 lg:pt-14">
        {/* Subtle Ambient Decorative Grids/Glows */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-accent-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 right-10 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
          
          {/* Main Grid: Left Column (Text & CTAs), Right Column (Illustration & Profile Card) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-8 items-center">
            
            {/* Left Content Column (7 cols on lg) */}
            <div className="lg:col-span-7 space-y-6 text-center lg:text-left">
              
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-xs text-slate-200">
                <span className="h-2 w-2 rounded-full bg-accent-500 animate-pulse" />
                <span className="font-medium">Track 1: Make MCP Matter · PM-RAHAT Scheme Ready</span>
              </div>

              {/* Main Heading */}
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.12]">
                Prepared Today.<br />
                <span className="text-accent-500">Supported</span> Always.
              </h1>

              {/* Supporting Text */}
              <p className="text-base sm:text-lg text-slate-300 max-w-xl mx-auto lg:mx-0 leading-relaxed">
                Your AI-powered companion for accident preparedness and aftermath management.
                From cashless hospital desks to police authentication and PM-RAHAT follow-ups.
              </p>

              {/* CTAs */}
              <div className="pt-2 flex flex-wrap items-center justify-center lg:justify-start gap-3 sm:gap-4">
                {/* Primary CTA: Report an Accident */}
                <button
                  onClick={onReportAccident}
                  className="group inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl font-semibold text-white bg-accent-500 hover:bg-accent-600 shadow-lg shadow-accent-500/25 transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
                >
                  <SirenIcon className="h-5 w-5 animate-bounce" />
                  <span className="text-sm sm:text-base">Report an Accident</span>
                  <ArrowRightIcon className="h-4 w-4 transform group-hover:translate-x-1 transition-transform" />
                </button>

                {/* Secondary CTA: Learn More */}
                <button
                  onClick={scrollToLearnMore}
                  className="inline-flex items-center gap-2 px-5 py-3.5 rounded-xl font-medium text-sm sm:text-base text-slate-200 bg-white/5 hover:bg-white/10 border border-slate-700/80 hover:border-slate-500 transition-all cursor-pointer"
                >
                  <InfoIcon className="h-4 w-4 text-slate-400" />
                  <span>Learn More</span>
                </button>
              </div>

              {/* Micro-assurances */}
              <div className="pt-2 flex flex-wrap items-center justify-center lg:justify-start gap-4 text-xs text-slate-400">
                <span className="flex items-center gap-1.5">
                  <span className="text-accent-500">✓</span> Official PIB/MoRTH text
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="text-accent-500">✓</span> Zero hallucinated rules
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="text-accent-500">✓</span> Family coordinator approval gate
                </span>
              </div>

            </div>

            {/* Right Column: Hero Illustration + Profile Readiness Card (5 cols on lg) */}
            <div className="lg:col-span-5 flex flex-col sm:flex-row lg:flex-col items-center justify-center gap-6">
              
              {/* Hero Illustration */}
              <div className="w-full max-w-[340px] sm:max-w-[280px] lg:max-w-[360px]">
                <HeroIllustration />
              </div>

              {/* Profile Readiness Card */}
              <div className="w-full max-w-sm">
                <ProfileReadinessCard
                  userName={user?.name || 'Priya Sharma'}
                  roleLabel={user?.role_label || 'Family Coordinator'}
                  onOpenProfile={onOpenProfile}
                  onOpenVehicles={onOpenVehicles}
                />
              </div>

            </div>

          </div>

        </div>
      </section>

      {/* ------------------------------------------------------------- Feature Cards */}
      <FeatureCards
        onOpenVehicles={onOpenVehicles}
        onOpenDocuments={onOpenDocuments}
        onOpenCases={onOpenCases}
        onOpenAI={onOpenAI}
      />

      {/* ------------------------------------------------------------- Information Strip */}
      <div id="info-strip-section">
        <InfoStrip
          onLearnMore={scrollToLearnMore}
          onOpenAI={onOpenAI}
        />
      </div>

      {/* ------------------------------------------------------------- PIB Scheme Stats & Presenter Controls */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 my-6 w-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {STATS.map((s) => (
            <div key={s.big} className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-sm hover:border-slate-300 transition">
              <div className="text-2xl sm:text-3xl font-extrabold text-navy-950 tracking-tight">{s.big}</div>
              <div className="text-xs sm:text-sm font-medium text-slate-700 mt-1 leading-snug">{s.label}</div>
              <div className="text-[11px] text-slate-400 mt-2 font-mono">{s.src}</div>
            </div>
          ))}
        </div>

        {/* Presenter & Demo Staging Box */}
        <div className="mt-6 rounded-2xl bg-white border border-slate-200/90 p-5 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-accent-500 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded-full">
                  Demo & Testing Controls
                </span>
                <span className="text-xs text-slate-500">Synthetic Scenario</span>
              </div>
              <h4 className="text-sm font-bold text-navy-900 mt-1">
                Stage Demo Case (SH-2026-0001 · Ravi Kumar)
              </h4>
              <p className="text-xs text-slate-500 max-w-2xl mt-0.5">
                Resets the synthetic case to Day 1 after the accident with hospital bill, medical report, ₹1,24,000 confirmed, and watcher alerts fired.
              </p>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                disabled={!!busy}
                onClick={() => stage(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-accent-500 text-white hover:bg-accent-600 transition disabled:opacity-50 shadow-sm"
              >
                {busy === 'stage' ? 'Staging via MCP…' : 'Stage Demo Case'}
              </button>
              <button
                disabled={!!busy}
                onClick={() => stage(true)}
                className="px-3 py-2 rounded-xl text-xs font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 transition disabled:opacity-50"
              >
                {busy === 'fresh' ? 'Resetting…' : 'Start Empty'}
              </button>
            </div>
          </div>
          {err && <div className="text-xs text-red-600 mt-2">{err}</div>}
        </div>
      </section>

      {/* ------------------------------------------------------------- Footer */}
      <footer className="mt-auto bg-navy-950 text-slate-400 border-t border-navy-900 py-10 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-center md:text-left">
          
          <div className="flex items-center gap-3">
            <ShieldLogo className="h-7 w-7" />
            <div>
              <div className="text-sm font-bold text-white tracking-wider">
                SECOND HOUR • BE READY. STAY SECURE.
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                The first hour belongs to doctors. The second hour belongs to the family.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-4 text-xs">
            <span className="text-slate-400">
              Emergency Services: <a href="tel:112" className="text-white font-bold underline">112</a>
            </span>
            <span className="hidden sm:inline text-slate-700">|</span>
            <span>PIB Press Release PRID 2238637 & 2298285</span>
            <span className="hidden sm:inline text-slate-700">|</span>
            <span>Synthetic Demo Data Only</span>
          </div>

        </div>

        <div className="max-w-6xl mx-auto mt-6 pt-6 border-t border-slate-800/80 text-center text-[11px] text-slate-400">
          Second Hour is an accident coordination platform. It does not provide legal advice, medical advice, or official government certifications.
        </div>
      </footer>
    </div>
  )
}
