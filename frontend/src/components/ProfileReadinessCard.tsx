import { CheckCircleIcon } from './Icons'

interface ProfileReadinessCardProps {
  userName?: string
  roleLabel?: string
  onOpenProfile?: () => void
  onOpenVehicles?: () => void
}

export function ProfileReadinessCard({
  userName = "Priya Sharma",
  roleLabel = "Family Coordinator",
  onOpenProfile,
  onOpenVehicles
}: ProfileReadinessCardProps) {
  const items = [
    { title: "Profile Information", detail: `${userName} (${roleLabel})`, done: true, onClick: onOpenProfile },
    { title: "Registered Vehicles", detail: "KA-01-MJ-2024 · Honda City", done: true, onClick: onOpenVehicles },
    { title: "Insurance Details", detail: "Comprehensive · PM-RAHAT Ready", done: true, onClick: onOpenVehicles },
    { title: "Emergency Contacts", detail: "Arjun Sharma (Brother)", done: true, onClick: onOpenProfile },
  ]

  const completedCount = items.filter(i => i.done).length
  const totalCount = items.length
  const percentage = Math.round((completedCount / totalCount) * 100)

  return (
    <div className="w-full max-w-sm rounded-2xl bg-navy-900/90 border border-slate-700/80 p-5 shadow-2xl backdrop-blur-md text-white transition hover:border-slate-600">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">Demo Profile Status</span>
          </div>
          <h3 className="text-base font-bold text-white mt-0.5">Your Profile Status</h3>
        </div>

        {/* Completion Indicator */}
        <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-1 rounded-full">
          <span className="text-xs font-bold text-emerald-400">{percentage}%</span>
          <span className="text-[11px] text-emerald-300 font-medium">{completedCount}/{totalCount}</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mt-3 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500" 
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Checklist */}
      <div className="mt-3.5 space-y-2.5">
        {items.map((item, idx) => (
          <div 
            key={idx}
            onClick={item.onClick}
            className="flex items-start gap-2.5 p-1.5 -mx-1.5 rounded-lg hover:bg-white/5 cursor-pointer transition"
          >
            <div className="mt-0.5 flex-shrink-0 text-emerald-400">
              <CheckCircleIcon className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-slate-200">{item.title}</div>
              <div className="text-[11px] text-slate-400 truncate">{item.detail}</div>
            </div>
            <span className="text-[10px] text-slate-500 font-medium">Verified</span>
          </div>
        ))}
      </div>

      {/* Next Reminder Box */}
      <div className="mt-4 pt-3 border-t border-slate-700/60">
        <div className="rounded-xl bg-accent-500/10 border border-accent-500/30 p-2.5 flex items-center justify-between">
          <div className="min-w-0">
            <div className="text-[10px] font-bold uppercase tracking-wider text-accent-500">Next Reminder</div>
            <div className="text-xs font-medium text-slate-200 truncate mt-0.5">Insurance Renewal — KA-01-MJ-2024</div>
            <div className="text-[11px] text-slate-400">Tata AIG Comprehensive · Due in 28 days</div>
          </div>
          <button 
            onClick={onOpenVehicles}
            className="flex-shrink-0 ml-2 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-accent-500 text-white hover:bg-accent-600 transition"
          >
            View
          </button>
        </div>
      </div>
    </div>
  )
}
