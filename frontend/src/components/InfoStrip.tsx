import { PhoneCallIcon, LandmarkIcon, ShieldCheckIcon, HeartHandIcon } from './Icons'

interface InfoStripProps {
  onLearnMore?: () => void
  onOpenAI?: () => void
}

export function InfoStrip({ onLearnMore, onOpenAI }: InfoStripProps) {
  return (
    <div className="max-w-6xl mx-auto px-4 mt-8 mb-10">
      <div className="rounded-2xl bg-white border border-slate-200/90 shadow-sm overflow-hidden">
        {/* The 4 Strip Columns */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-slate-200/80">
          
          {/* 1. Emergency Assistance */}
          <div className="p-4 sm:p-5 flex items-start gap-3.5 hover:bg-slate-50/80 transition">
            <div className="h-10 w-10 rounded-xl bg-red-50 text-red-600 border border-red-100 flex items-center justify-center flex-shrink-0">
              <PhoneCallIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h4 className="text-sm font-bold text-navy-950">Emergency Assistance</h4>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700">24x7</span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                In case of emergency, call{' '}
                <a 
                  href="tel:112" 
                  className="font-bold text-red-600 hover:text-red-700 underline"
                  title="Call Emergency Services immediately"
                >
                  112
                </a>.
              </p>
              <div className="text-[11px] text-slate-400 mt-1">National Emergency Helpline</div>
            </div>
          </div>

          {/* 2. PM-RAHAT Guidance */}
          <div 
            onClick={onOpenAI}
            className="p-4 sm:p-5 flex items-start gap-3.5 hover:bg-slate-50/80 transition cursor-pointer"
          >
            <div className="h-10 w-10 rounded-xl bg-amber-50 text-amber-600 border border-amber-100 flex items-center justify-center flex-shrink-0">
              <LandmarkIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-bold text-navy-950">PM-RAHAT Guidance</h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Guidance on PM-RAHAT Scheme (up to ₹1.5L / 7 days).
              </p>
              <div className="text-[11px] text-accent-500 font-medium mt-1 flex items-center gap-1">
                <span>Ask scheme agent</span>
                <span>→</span>
              </div>
            </div>
          </div>

          {/* 3. Insurance & Claims */}
          <div 
            onClick={onLearnMore}
            className="p-4 sm:p-5 flex items-start gap-3.5 hover:bg-slate-50/80 transition cursor-pointer"
          >
            <div className="h-10 w-10 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 flex items-center justify-center flex-shrink-0">
              <ShieldCheckIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-bold text-navy-950">Insurance & Claims</h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Assistance for insurance and claims follow-up.
              </p>
              <div className="text-[11px] text-blue-600 font-medium mt-1">Hospital bill coordination</div>
            </div>
          </div>

          {/* 4. Family Support */}
          <div 
            onClick={onLearnMore}
            className="p-4 sm:p-5 flex items-start gap-3.5 hover:bg-slate-50/80 transition cursor-pointer"
          >
            <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 flex items-center justify-center flex-shrink-0">
              <HeartHandIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h4 className="text-sm font-bold text-navy-950">Family Support</h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Shared case view and tasks for family members.
              </p>
              <div className="text-[11px] text-emerald-600 font-medium mt-1">Priya & Arjun shared desk</div>
            </div>
          </div>

        </div>

        {/* Disclaimer Bar */}
        <div className="bg-slate-50/80 border-t border-slate-200/80 px-4 sm:px-6 py-2.5 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 gap-1 text-center sm:text-left">
          <span>
            <strong className="text-slate-700">Notice:</strong> Second Hour is an independent assistance and coordination tool. It is not an official emergency service or government agency.
          </span>
          <span className="font-semibold text-slate-600">Synthetic demo data only</span>
        </div>
      </div>
    </div>
  )
}
