import { useState } from 'react'
import type { NotificationPreferences } from './types'

interface NotificationPreferencesSectionProps {
  preferences: NotificationPreferences
  onSave: (data: Partial<NotificationPreferences>) => Promise<void>
}

export function NotificationPreferencesSection({
  preferences,
  onSave,
}: NotificationPreferencesSectionProps) {
  const [channels, setChannels] = useState({
    email_notifications: preferences.channels.email_notifications,
    sms_notifications: preferences.channels.sms_notifications,
    in_app_notifications: preferences.channels.in_app_notifications,
    whatsapp_notifications: preferences.channels.whatsapp_notifications,
  })

  const [alerts, setAlerts] = useState({
    accident_alerts: preferences.alerts.accident_alerts,
    case_updates: preferences.alerts.case_updates,
    document_expiry_reminders: preferences.alerts.document_expiry_reminders,
    insurance_renewal_reminders: preferences.alerts.insurance_renewal_reminders,
    pending_task_reminders: preferences.alerts.pending_task_reminders,
  })

  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const handleToggleChannel = async (key: keyof typeof channels) => {
    const updated = { ...channels, [key]: !channels[key] }
    setChannels(updated)
    try {
      setSaving(true)
      await onSave({ channels: updated, alerts })
      setNotice('Notification channel preference updated.')
      setTimeout(() => setNotice(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  const handleToggleAlert = async (key: keyof typeof alerts) => {
    const updated = { ...alerts, [key]: !alerts[key] }
    setAlerts(updated)
    try {
      setSaving(true)
      await onSave({ channels, alerts: updated })
      setNotice('Alert preference updated.')
      setTimeout(() => setNotice(null), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden space-y-6">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900">Notification Preferences</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Select communication channels and choose which alerts Second Hour delivers to you.
        </p>
      </div>

      {notice && (
        <div className="mx-5 sm:mx-6 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 font-medium">
          {notice}
        </div>
      )}

      {/* 1. Delivery Channels */}
      <div className="px-5 sm:px-6 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Delivery Channels
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Email */}
          <div className="p-4 rounded-xl border border-slate-200 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-slate-900">Email Notifications</p>
              <p className="text-[11px] text-slate-500">Case milestone digests and official reports</p>
            </div>
            <input
              type="checkbox"
              disabled={saving}
              checked={channels.email_notifications}
              onChange={() => handleToggleChannel('email_notifications')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* SMS */}
          <div className="p-4 rounded-xl border border-slate-200 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-slate-900">SMS Alerts</p>
              <p className="text-[11px] text-slate-500">High-priority crash SOS and hospital updates</p>
            </div>
            <input
              type="checkbox"
              disabled={saving}
              checked={channels.sms_notifications}
              onChange={() => handleToggleChannel('sms_notifications')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* In-App */}
          <div className="p-4 rounded-xl border border-slate-200 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold text-slate-900">In-App Notifications</p>
              <p className="text-[11px] text-slate-500">Bell alerts inside the Second Hour portal</p>
            </div>
            <input
              type="checkbox"
              disabled={saving}
              checked={channels.in_app_notifications}
              onChange={() => handleToggleChannel('in_app_notifications')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* WhatsApp (Beta/Disabled) */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 flex items-center justify-between opacity-80">
            <div>
              <div className="flex items-center gap-1.5">
                <p className="text-xs font-bold text-slate-900">WhatsApp Dispatch</p>
                <span className="text-[10px] font-semibold px-2 py-0.2 rounded bg-slate-200 text-slate-700">
                  Coming Soon
                </span>
              </div>
              <p className="text-[11px] text-slate-500">Official WhatsApp Business integration in pilot</p>
            </div>
            <input
              type="checkbox"
              disabled
              checked={channels.whatsapp_notifications}
              className="rounded text-slate-400 cursor-not-allowed"
            />
          </div>
        </div>
      </div>

      {/* 2. Alert Subscriptions */}
      <div className="p-5 sm:p-6 pt-0 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Alert Subscriptions
        </h3>

        <div className="space-y-2.5">
          {/* Accident Alert */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-rose-200 bg-rose-50/30">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-rose-950">Accident Alerts (Critical)</span>
                <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-rose-100 text-rose-800">
                  Mandatory for SOS
                </span>
              </div>
              <p className="text-[11px] text-slate-600">Immediate alerts during reported accidents and hospital admissions.</p>
            </div>
            <input
              type="checkbox"
              checked={alerts.accident_alerts}
              onChange={() => handleToggleAlert('accident_alerts')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Case Updates */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50">
            <div>
              <p className="text-xs font-bold text-slate-900">Case Milestone Updates</p>
              <p className="text-[11px] text-slate-500">Notifications when treating doctor, police draft, or PM-RAHAT changes state.</p>
            </div>
            <input
              type="checkbox"
              checked={alerts.case_updates}
              onChange={() => handleToggleAlert('case_updates')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Document Expiry */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50">
            <div>
              <p className="text-xs font-bold text-slate-900">Document Expiry Reminders</p>
              <p className="text-[11px] text-slate-500">Advance 30-day and 7-day warnings before Driving Licence or PUC expires.</p>
            </div>
            <input
              type="checkbox"
              checked={alerts.document_expiry_reminders}
              onChange={() => handleToggleAlert('document_expiry_reminders')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Insurance Renewal */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50">
            <div>
              <p className="text-xs font-bold text-slate-900">Vehicle Insurance Renewal Reminders</p>
              <p className="text-[11px] text-slate-500">Alerts to prevent policy lapse on registered vehicles.</p>
            </div>
            <input
              type="checkbox"
              checked={alerts.insurance_renewal_reminders}
              onChange={() => handleToggleAlert('insurance_renewal_reminders')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>

          {/* Pending Tasks */}
          <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 hover:bg-slate-50">
            <div>
              <p className="text-xs font-bold text-slate-900">Pending Action Item Reminders</p>
              <p className="text-[11px] text-slate-500">Reminders for police draft reviews, document uploads, and surveyor visits.</p>
            </div>
            <input
              type="checkbox"
              checked={alerts.pending_task_reminders}
              onChange={() => handleToggleAlert('pending_task_reminders')}
              className="rounded text-[#ff7518] focus:ring-[#ff7518]"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
