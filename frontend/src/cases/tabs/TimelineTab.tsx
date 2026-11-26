import type { TimelineEventItem } from '../types'
import { fmtTime } from '../../api'

interface TimelineTabProps {
  timeline: TimelineEventItem[]
  onRefresh: () => void
}

export function TimelineTab({ timeline }: TimelineTabProps) {
  const getEventIcon = (kind: string) => {
    switch (kind) {
      case 'incident_occurred':
        return '🚨'
      case 'hospital_admission':
        return '🏥'
      case 'pmrahat_activated':
        return '🛡️'
      case 'case_created':
        return '📋'
      case 'insurance_claim_intimated':
        return '📑'
      case 'police_draft_prepared':
      case 'police_draft_approved':
        return '👮'
      case 'evidence_uploaded':
        return '📷'
      case 'task_status':
      case 'task_created':
        return '☑️'
      case 'member_added':
        return '👥'
      default:
        return '📌'
    }
  }

  return (
    <div className="card p-6 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-6">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
            <span>⏱️</span>
            <span>Case Activity Timeline</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Chronological audit trail of verified updates, hospital records, and police documentation
          </p>
        </div>
        <div className="text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
          {timeline.length} Events Logged
        </div>
      </div>

      <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
        {timeline.map((ev, idx) => {
          const icon = getEventIcon(ev.kind)
          return (
            <div key={ev.id || idx} className="relative group">
              {/* Circle Marker */}
              <div className="absolute -left-6 sm:-left-8 top-0.5 w-6 h-6 rounded-full bg-white border-2 border-navy-900 flex items-center justify-center text-xs shadow-xs group-hover:border-accent-500 transition">
                <span>{icon}</span>
              </div>

              {/* Event Content Box */}
              <div className="bg-slate-50/70 hover:bg-slate-50 p-4 rounded-xl border border-slate-100 transition space-y-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold text-navy-900 capitalize">
                    {ev.kind.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    {fmtTime(ev.at)} IST
                  </span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed font-medium">
                  {ev.summary}
                </p>
                <div className="text-[11px] text-slate-400 pt-1 flex items-center gap-1.5">
                  <span>Actor / Origin:</span>
                  <span className="font-semibold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200 text-[10px]">
                    {ev.actor_name || 'System Auto-Log'}
                  </span>
                </div>
              </div>
            </div>
          )
        })}

        {timeline.length === 0 && (
          <div className="text-center py-8 text-xs text-slate-500">
            No timeline events recorded yet.
          </div>
        )}
      </div>
    </div>
  )
}
