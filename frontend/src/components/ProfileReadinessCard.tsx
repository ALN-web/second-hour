import { SolidGreenCheck, SolidGreenShieldIcon, CalendarReminderIcon, ChevronRightIcon } from './Icons'

interface ProfileReadinessCardProps {
  onOpenProfile?: () => void
  onOpenVehicles?: () => void
}

export function ProfileReadinessCard({
  onOpenProfile,
  onOpenVehicles
}: ProfileReadinessCardProps) {
  const items = [
    { title: "Profile Information", onClick: onOpenProfile },
    { title: "Registered Vehicles", onClick: onOpenVehicles },
    { title: "Insurance Details", onClick: onOpenVehicles },
    { title: "Emergency Contacts", onClick: onOpenProfile },
  ]

  return (
    <div className="w-full max-w-[340px] rounded-2xl bg-[#0d223f]/95 border border-[#1e3b63] p-5 shadow-2xl backdrop-blur-md text-white transition hover:border-[#2b4d7e]">
      
      {/* Header */}
      <div className="flex items-center justify-between pb-4">
        <div className="flex items-center gap-2">
          <SolidGreenShieldIcon className="h-5 w-5 flex-shrink-0" />
          <h3 className="text-sm font-bold text-white tracking-tight">Your Profile Status</h3>
        </div>

        {/* Complete Pill */}
        <span className="bg-[#059669] text-white px-2.5 py-0.5 rounded-full text-[11px] font-semibold tracking-wide">
          Complete
        </span>
      </div>

      {/* Checklist */}
      <div className="space-y-3 pb-4">
        {items.map((item, idx) => (
          <div
            key={idx}
            onClick={item.onClick}
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <SolidGreenCheck className="h-4 w-4 flex-shrink-0" />
            <span className="text-xs font-medium text-slate-200 group-hover:text-white transition">
              {item.title}
            </span>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="border-t border-[#1a3559] pt-3.5">
        <div 
          onClick={onOpenVehicles}
          className="flex items-center justify-between cursor-pointer group hover:bg-white/5 p-1.5 -mx-1.5 rounded-xl transition"
        >
          <div className="flex items-start gap-3">
            <CalendarReminderIcon className="h-5 w-5 text-slate-300 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-[11px] text-slate-400 font-medium leading-none">Next Reminder</div>
              <div className="text-xs font-bold text-white mt-1 group-hover:text-accent-500 transition">
                Insurance Renewal
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">Apr 15, 2026</div>
            </div>
          </div>

          <div className="text-slate-400 group-hover:text-white transition pl-2">
            <ChevronRightIcon className="h-4 w-4" />
          </div>
        </div>
      </div>

    </div>
  )
}
