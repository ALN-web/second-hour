import { PulseHeartIcon, AshokaEmblemIcon, SolidGreenShieldIcon, HandshakeIcon } from './Icons'

interface InfoStripProps {
  onLearnMore?: () => void
  onOpenAI?: () => void
}

export function InfoStrip({ onLearnMore, onOpenAI }: InfoStripProps) {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 mt-6 mb-12">
      <div className="rounded-2xl bg-white border border-slate-200/90 shadow-sm overflow-hidden py-3 px-2 sm:px-4">
        {/* 4 Items in a Row with Dividers */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-slate-200">
          
          {/* 1. Emergency Assistance */}
          <div className="px-4 py-3 flex items-center gap-3">
            <div className="flex-shrink-0">
              <PulseHeartIcon className="h-6 w-6" />
            </div>
            <div className="text-xs text-slate-700 font-medium">
              In case of emergency, call{' '}
              <a 
                href="tel:112" 
                className="font-bold text-[#ff7a18] hover:underline"
              >
                112
              </a>
            </div>
          </div>

          {/* 2. PM-RAHAT Guidance */}
          <div 
            onClick={onOpenAI}
            className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-slate-50/80 transition"
          >
            <div className="text-slate-800 flex-shrink-0">
              <AshokaEmblemIcon className="h-6 w-6" />
            </div>
            <div className="text-xs text-slate-700 font-medium">
              Guidance on PM-RAHAT Scheme
            </div>
          </div>

          {/* 3. Insurance & Claims */}
          <div 
            onClick={onLearnMore}
            className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-slate-50/80 transition"
          >
            <div className="flex-shrink-0">
              <SolidGreenShieldIcon className="h-5 w-5" />
            </div>
            <div className="text-xs text-slate-700 font-medium">
              Assistance for insurance & claims
            </div>
          </div>

          {/* 4. Family Support */}
          <div 
            onClick={onLearnMore}
            className="px-4 py-3 flex items-center gap-3 cursor-pointer hover:bg-slate-50/80 transition"
          >
            <div className="text-slate-700 flex-shrink-0">
              <HandshakeIcon className="h-5 w-5" />
            </div>
            <div className="text-xs text-slate-700 font-medium">
              Support for your family
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
