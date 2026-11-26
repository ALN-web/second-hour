import { useState } from 'react'
import { SirenIcon, ArrowRightIcon, InfoIcon } from './Icons'
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

export function Homepage({
  user: _user,
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
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans antialiased text-slate-800">
      
      {/* ========================================================= HERO SECTION */}
      <section className="relative bg-[#091528] text-white overflow-hidden pb-16 lg:pb-20 pt-6 sm:pt-10">
        
        {/* Soft radial blue lighting behind center illustration */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[500px] bg-[#1e40af]/15 rounded-full blur-[100px] pointer-events-none" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            
            {/* Left Column: Heading, Subtitle & Pill CTAs (5 cols) */}
            <div className="lg:col-span-5 space-y-6 text-center lg:text-left">
              
              {/* Main Heading */}
              <h1 className="text-4xl sm:text-5xl lg:text-[54px] font-extrabold tracking-tight text-white leading-[1.12]">
                Prepared Today.<br />
                <span className="text-[#ff7a18]">Supported</span> Always.
              </h1>

              {/* Supporting Subtitle */}
              <p className="text-sm sm:text-base text-slate-300 max-w-md mx-auto lg:mx-0 leading-relaxed font-normal">
                Your AI-powered companion for accident preparedness and aftermath management.
              </p>

              {/* Action Buttons: Full Rounded Pills */}
              <div className="pt-2 flex flex-wrap items-center justify-center lg:justify-start gap-3.5">
                
                {/* Primary CTA: Report an Accident */}
                <button
                  onClick={onReportAccident}
                  className="inline-flex items-center gap-2.5 px-6 py-3 rounded-full font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] shadow-lg shadow-[#ff7518]/25 transition-all duration-200 hover:scale-[1.02] cursor-pointer"
                >
                  <SirenIcon className="h-4 w-4" />
                  <span className="text-sm">Report an Accident</span>
                  <ArrowRightIcon className="h-3.5 w-3.5" />
                </button>

                {/* Secondary CTA: Learn More */}
                <button
                  onClick={scrollToLearnMore}
                  className="inline-flex items-center gap-2 px-5 py-3 rounded-full font-medium text-sm text-slate-200 bg-[#12233c] hover:bg-[#182e4e] border border-[#243e65] transition-all cursor-pointer"
                >
                  <InfoIcon className="h-4 w-4 text-slate-400" />
                  <span>Learn More</span>
                </button>

              </div>

            </div>

            {/* Center: Hero Curved Road & Shield Illustration (4 cols) */}
            <div className="lg:col-span-4 flex items-center justify-center">
              <HeroIllustration className="w-full max-w-[360px] lg:max-w-[420px]" />
            </div>

            {/* Right: Profile Readiness Card (3 cols) */}
            <div className="lg:col-span-3 flex justify-center lg:justify-end">
              <ProfileReadinessCard
                onOpenProfile={onOpenProfile}
                onOpenVehicles={onOpenVehicles}
              />
            </div>

          </div>

        </div>
      </section>

      {/* ========================================================= MAIN FEATURE CARDS */}
      <FeatureCards
        onOpenVehicles={onOpenVehicles}
        onOpenDocuments={onOpenDocuments}
        onOpenCases={onOpenCases}
        onOpenAI={onOpenAI}
      />

      {/* ========================================================= INFORMATION STRIP */}
      <div id="info-strip-section">
        <InfoStrip
          onLearnMore={scrollToLearnMore}
          onOpenAI={onOpenAI}
        />
      </div>

      {/* ========================================================= DEMO CONTROLS (Non-intrusive) */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 mb-8 w-full">
        <div className="rounded-xl border border-slate-200 bg-white p-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="font-semibold text-slate-800">PM-RAHAT Cashless Demo Engine</span>
            <span className="text-slate-400">|</span>
            <span>SH-2026-0001 (Ravi Kumar · Bengaluru)</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={!!busy}
              onClick={() => stage(false)}
              className="px-3 py-1.5 rounded-lg font-semibold bg-[#ff7518] text-white hover:bg-[#ea6309] transition disabled:opacity-50"
            >
              {busy === 'stage' ? 'Staging…' : 'Stage Demo Case'}
            </button>
            <button
              disabled={!!busy}
              onClick={() => stage(true)}
              className="px-3 py-1.5 rounded-lg font-medium border border-slate-300 hover:bg-slate-50 transition disabled:opacity-50"
            >
              {busy === 'fresh' ? 'Resetting…' : 'Start Empty'}
            </button>
          </div>
        </div>
        {err && <div className="text-xs text-red-600 mt-1">{err}</div>}
      </div>

      {/* ========================================================= FOOTER */}
      <footer className="mt-auto bg-[#091528] text-slate-400 py-6 border-t border-[#13243d]">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <div className="text-xs font-bold tracking-[0.2em] text-white uppercase">
            SECOND HOUR &nbsp;•&nbsp; BE READY. STAY SECURE.
          </div>
          <div className="text-[10px] text-slate-500 mt-2">
            Official PM-RAHAT PIB Guidance · Emergency Helpline: 112 · Synthetic Demo Environment
          </div>
        </div>
      </footer>

    </div>
  )
}
