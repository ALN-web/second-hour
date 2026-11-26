import { FrontCarIcon, DocumentCardIcon, ShieldCheckCardIcon, RobotAssistantIcon, ArrowRightIcon } from './Icons'

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
      desc: 'Manage your vehicles and insurance details',
      icon: FrontCarIcon,
      iconBg: 'bg-[#ebf3ff] text-[#2563eb]',
      onClick: onOpenVehicles,
    },
    {
      id: 'documents',
      title: 'My Documents',
      desc: 'Access your important documents',
      icon: DocumentCardIcon,
      iconBg: 'bg-[#fff4eb] text-[#ea580c]',
      onClick: onOpenDocuments,
    },
    {
      id: 'cases',
      title: 'My Cases',
      desc: 'Track your accident cases and progress',
      icon: ShieldCheckCardIcon,
      iconBg: 'bg-[#edfbf2] text-[#16a34a]',
      onClick: onOpenCases,
    },
    {
      id: 'ai',
      title: 'Ask Second Hour AI',
      desc: 'Get instant help and guidance',
      icon: RobotAssistantIcon,
      iconBg: 'bg-[#f3efff] text-[#7c3aed]',
      onClick: onOpenAI,
    },
  ]

  return (
    <div className="relative z-20 -mt-10 lg:-mt-14 max-w-6xl mx-auto px-4 sm:px-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <div
              key={card.id}
              onClick={card.onClick}
              className="relative flex items-start gap-4 rounded-2xl bg-white border border-slate-200/90 p-5 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1 cursor-pointer select-none group min-h-[120px]"
            >
              {/* Circular Icon Container */}
              <div className={`h-12 w-12 rounded-full flex items-center justify-center flex-shrink-0 transition-transform duration-300 group-hover:scale-105 ${card.iconBg}`}>
                <Icon className="h-6 w-6" />
              </div>

              {/* Text Content */}
              <div className="min-w-0 flex-1 pr-6">
                <h3 className="text-sm font-bold text-navy-950 group-hover:text-accent-500 transition">
                  {card.title}
                </h3>
                <p className="mt-1 text-xs text-slate-500 leading-snug">
                  {card.desc}
                </p>
              </div>

              {/* Bottom-Right Arrow Circle */}
              <div className="absolute bottom-4 right-4 h-6 w-6 rounded-full bg-[#f0f6ff] text-[#2563eb] flex items-center justify-center transition-all group-hover:bg-accent-500 group-hover:text-white">
                <ArrowRightIcon className="h-3 w-3 transform group-hover:translate-x-0.5 transition-transform" />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
