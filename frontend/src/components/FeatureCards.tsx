import { CarIcon, DocumentIcon, ShieldCheckIcon, RobotIcon, ArrowRightIcon } from './Icons'

interface FeatureCardsProps {
  onOpenVehicles: () => void
  onOpenDocuments: () => void
  onOpenCases: () => void
  onOpenAI: () => void
}

export function FeatureCards({
  onOpenVehicles,
  onOpenDocuments,
  onOpenCases,
  onOpenAI
}: FeatureCardsProps) {
  const cards = [
    {
      id: 'vehicles',
      title: 'My Vehicles',
      desc: 'Manage your vehicles and insurance details.',
      icon: CarIcon,
      containerColor: 'bg-blue-50 text-blue-600 border-blue-100 group-hover:bg-blue-600 group-hover:text-white',
      accentBorder: 'hover:border-blue-300',
      tag: '1 Active Vehicle',
      tagColor: 'bg-blue-50 text-blue-700',
      onClick: onOpenVehicles,
    },
    {
      id: 'documents',
      title: 'My Documents',
      desc: 'Access your important documents.',
      icon: DocumentIcon,
      containerColor: 'bg-orange-50 text-orange-600 border-orange-100 group-hover:bg-orange-600 group-hover:text-white',
      accentBorder: 'hover:border-orange-300',
      tag: 'Document Vault',
      tagColor: 'bg-orange-50 text-orange-700',
      onClick: onOpenDocuments,
    },
    {
      id: 'cases',
      title: 'My Cases',
      desc: 'Track your accident cases and progress.',
      icon: ShieldCheckIcon,
      containerColor: 'bg-emerald-50 text-emerald-600 border-emerald-100 group-hover:bg-emerald-600 group-hover:text-white',
      accentBorder: 'hover:border-emerald-300',
      tag: 'Live Case Status',
      tagColor: 'bg-emerald-50 text-emerald-700',
      onClick: onOpenCases,
    },
    {
      id: 'ai',
      title: 'Ask Second Hour AI',
      desc: 'Get instant help and guidance.',
      icon: RobotIcon,
      containerColor: 'bg-purple-50 text-purple-600 border-purple-100 group-hover:bg-purple-600 group-hover:text-white',
      accentBorder: 'hover:border-purple-300',
      tag: 'PM-RAHAT Agent',
      tagColor: 'bg-purple-50 text-purple-700',
      onClick: onOpenAI,
    },
  ]

  return (
    <div className="relative z-10 -mt-12 lg:-mt-16 max-w-6xl mx-auto px-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <div
              key={card.id}
              onClick={card.onClick}
              className={`group relative flex flex-col justify-between rounded-2xl bg-white border border-slate-200/90 p-5 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1.5 cursor-pointer select-none ${card.accentBorder}`}
            >
              <div>
                {/* Top: Icon + Badge */}
                <div className="flex items-center justify-between">
                  <div className={`h-12 w-12 rounded-2xl border flex items-center justify-center transition-colors duration-300 ${card.containerColor}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${card.tagColor}`}>
                    {card.tag}
                  </span>
                </div>

                {/* Content */}
                <h3 className="mt-4 text-base font-bold text-navy-900 group-hover:text-navy-800 transition">
                  {card.title}
                </h3>
                <p className="mt-1 text-xs text-slate-500 leading-relaxed">
                  {card.desc}
                </p>
              </div>

              {/* Bottom Arrow Indicator */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 group-hover:text-slate-700 transition">
                <span className="font-medium text-[11px]">Open section</span>
                <div className="h-7 w-7 rounded-full bg-slate-100 group-hover:bg-accent-500 group-hover:text-white flex items-center justify-center transition-colors">
                  <ArrowRightIcon className="h-3.5 w-3.5 transform group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
