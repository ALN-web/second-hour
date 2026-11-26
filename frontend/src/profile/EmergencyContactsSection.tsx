import { useState } from 'react'
import type { EmergencyContactItem } from './types'

interface EmergencyContactsSectionProps {
  contacts: EmergencyContactItem[]
  onAddContact: (data: any) => Promise<void>
  onUpdateContact: (id: string, data: any) => Promise<void>
  onDeleteContact: (id: string) => Promise<void>
  onSetPrimary: (id: string) => Promise<void>
  onReorder: (ids: string[]) => Promise<void>
}

export function EmergencyContactsSection({
  contacts,
  onAddContact,
  onUpdateContact,
  onDeleteContact,
  onSetPrimary,
  onReorder,
}: EmergencyContactsSectionProps) {
  const [modalOpen, setModalOpen] = useState(false)
  const [editingContact, setEditingContact] = useState<EmergencyContactItem | null>(null)
  const [permissionModalContact, setPermissionModalContact] = useState<EmergencyContactItem | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Move priority up or down
  const handleMove = async (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= contacts.length) return

    const newOrder = [...contacts]
    const temp = newOrder[index]
    newOrder[index] = newOrder[targetIndex]
    newOrder[targetIndex] = temp

    try {
      setBusy(true)
      await onReorder(newOrder.map(c => c.id))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Emergency Contacts</h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-rose-50 text-rose-700 border border-rose-200">
              Critical
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Designated family and emergency responders notified during road accidents and aftermath tracking.
          </p>
        </div>

        <button
          onClick={() => {
            setEditingContact(null)
            setModalOpen(true)
          }}
          className="px-4 py-2 text-xs font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition shadow-md shadow-[#ff7518]/20 flex items-center justify-center gap-1.5 cursor-pointer shrink-0"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M12 4v16m8-8H4" />
          </svg>
          <span>Add Emergency Contact</span>
        </button>
      </div>

      {/* Notice info */}
      <div className="mx-5 sm:mx-6 mt-5 p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-2.5">
        <svg className="w-4 h-4 text-[#ff7518] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="leading-relaxed">
          Your <strong>Primary Contact</strong> receives automated accident dispatch alerts and hospital coordination updates. Granular permissions (case access, documents, medical) are configured per contact below and strictly enforced.
        </p>
      </div>

      {/* Contacts List */}
      <div className="p-5 sm:p-6 space-y-4">
        {contacts.length === 0 ? (
          <div className="text-center py-12 px-4 border border-dashed border-slate-200 rounded-2xl">
            <div className="w-12 h-12 mx-auto rounded-full bg-rose-50 text-rose-500 flex items-center justify-center mb-3">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
            <h3 className="text-sm font-bold text-slate-800">No Emergency Contacts Registered</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              Adding trusted family members ensures Second Hour can coordinate hospitalization and immediate support.
            </p>
          </div>
        ) : (
          contacts.map((contact, index) => (
            <div
              key={contact.id}
              className={`p-4 sm:p-5 rounded-2xl border transition-all ${
                contact.is_primary
                  ? 'border-[#ff7518]/50 bg-gradient-to-r from-orange-50/30 to-amber-50/10 shadow-sm'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                {/* Contact Identity */}
                <div className="flex items-start gap-3.5">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 ${
                    contact.is_primary ? 'bg-[#ff7518] text-white shadow-md shadow-[#ff7518]/25' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {contact.full_name.slice(0, 2).toUpperCase()}
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-900">{contact.full_name}</h3>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                        {contact.relationship}
                      </span>
                      {contact.is_primary && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-orange-100 text-orange-800 border border-orange-200 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#ff7518]" />
                          Primary Contact
                        </span>
                      )}
                      <span className="text-[10px] font-medium text-slate-400">
                        Priority {contact.priority}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-0.5">
                      <span className="font-mono">{contact.mobile_number}</span>
                      {contact.alternate_number && (
                        <span className="text-slate-400 font-mono">Alt: {contact.alternate_number}</span>
                      )}
                      {contact.email && (
                        <span>{contact.email}</span>
                      )}
                      <span className="capitalize text-slate-400">Method: {contact.preferred_contact_method}</span>
                    </div>
                  </div>
                </div>

                {/* Controls & Actions */}
                <div className="flex flex-wrap items-center gap-2 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-100">
                  {/* Reorder Buttons */}
                  <div className="flex items-center gap-1 mr-1">
                    <button
                      onClick={() => handleMove(index, 'up')}
                      disabled={index === 0 || busy}
                      className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 disabled:opacity-30 cursor-pointer"
                      title="Move Priority Up"
                    >
                      ▲
                    </button>
                    <button
                      onClick={() => handleMove(index, 'down')}
                      disabled={index === contacts.length - 1 || busy}
                      className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-50 disabled:opacity-30 cursor-pointer"
                      title="Move Priority Down"
                    >
                      ▼
                    </button>
                  </div>

                  {!contact.is_primary && (
                    <button
                      onClick={() => onSetPrimary(contact.id)}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition cursor-pointer"
                    >
                      Set Primary
                    </button>
                  )}

                  <button
                    onClick={() => setPermissionModalContact(contact)}
                    className="px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl transition flex items-center gap-1 cursor-pointer"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                    <span>Permissions</span>
                  </button>

                  <button
                    onClick={() => {
                      setEditingContact(contact)
                      setModalOpen(true)
                    }}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
                    title="Edit Contact"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>

                  {deleteConfirmId === contact.id ? (
                    <div className="flex items-center gap-1 bg-red-50 p-1 rounded-xl border border-red-200">
                      <span className="text-[11px] text-red-700 px-1 font-semibold">Delete?</span>
                      <button
                        onClick={() => {
                          onDeleteContact(contact.id)
                          setDeleteConfirmId(null)
                        }}
                        className="px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white text-[10px] font-bold rounded-lg"
                      >
                        Yes
                      </button>
                      <button
                        onClick={() => setDeleteConfirmId(null)}
                        className="px-2 py-0.5 text-slate-600 hover:text-slate-900 text-[10px] rounded-lg"
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirmId(contact.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition cursor-pointer"
                      title="Delete Contact"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Add / Edit Contact Modal */}
      {modalOpen && (
        <ContactFormModal
          contact={editingContact}
          onClose={() => {
            setModalOpen(false)
            setEditingContact(null)
          }}
          onSave={async (data) => {
            if (editingContact) {
              await onUpdateContact(editingContact.id, data)
            } else {
              await onAddContact(data)
            }
            setModalOpen(false)
            setEditingContact(null)
          }}
        />
      )}

      {/* Permissions Modal */}
      {permissionModalContact && (
        <ContactPermissionsModal
          contact={permissionModalContact}
          onClose={() => setPermissionModalContact(null)}
          onSave={async (perms) => {
            await onUpdateContact(permissionModalContact.id, { permissions: perms })
            setPermissionModalContact(null)
          }}
        />
      )}
    </div>
  )
}

function ContactFormModal({
  contact,
  onClose,
  onSave,
}: {
  contact: EmergencyContactItem | null
  onClose: () => void
  onSave: (data: any) => Promise<void>
}) {
  const [formData, setFormData] = useState({
    full_name: contact?.full_name || '',
    relationship: contact?.relationship || 'Parent',
    mobile_number: contact?.mobile_number || '',
    alternate_number: contact?.alternate_number || '',
    email: contact?.email || '',
    preferred_contact_method: contact?.preferred_contact_method || 'phone',
    is_primary: contact?.is_primary || false,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.full_name.trim() || !formData.mobile_number.trim()) {
      setError('Full name and mobile number are required.')
      return
    }

    try {
      setSubmitting(true)
      setError(null)
      await onSave(formData)
    } catch (err: any) {
      setError(err?.message || 'Failed to save contact.')
    } finally {
      setSubmitting(false)
    }
  }

  const relationships = ['Parent', 'Spouse', 'Sibling', 'Child', 'Relative', 'Friend', 'Other']

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className="bg-[#091528] text-white p-5 flex items-center justify-between">
          <h3 className="text-base font-bold text-white">
            {contact ? 'Edit Emergency Contact' : 'Register Emergency Contact'}
          </h3>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-800 font-medium">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="e.g. Arjun Sharma"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Relationship *</label>
              <select
                value={formData.relationship}
                onChange={(e) => setFormData({ ...formData, relationship: e.target.value })}
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              >
                {relationships.map(r => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Primary Mobile *</label>
              <input
                type="tel"
                required
                value={formData.mobile_number}
                onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })}
                placeholder="+91 98450 00000"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Alternate Phone</label>
              <input
                type="tel"
                value={formData.alternate_number}
                onChange={(e) => setFormData({ ...formData, alternate_number: e.target.value })}
                placeholder="e.g. +91 80 2521 0000"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="contact@example.com"
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Preferred Contact Method</label>
              <select
                value={formData.preferred_contact_method}
                onChange={(e) => setFormData({ ...formData, preferred_contact_method: e.target.value })}
                className="w-full text-xs rounded-xl border border-slate-300 px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-[#ff7518]"
              >
                <option value="phone">Phone Call</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="sms">SMS Text</option>
              </select>
            </div>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_primary}
                onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
                className="rounded text-[#ff7518] focus:ring-[#ff7518]"
              />
              <span className="text-xs text-slate-700 font-semibold">
                Set as Primary Emergency Contact (demotes existing primary contact)
              </span>
            </label>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-xl transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-xs font-semibold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition shadow-md shadow-[#ff7518]/20 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save Contact'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ContactPermissionsModal({
  contact,
  onClose,
  onSave,
}: {
  contact: EmergencyContactItem
  onClose: () => void
  onSave: (perms: any) => Promise<void>
}) {
  const [perms, setPerms] = useState({
    can_notify_accident: contact.permissions?.can_notify_accident ?? true,
    can_receive_case_updates: contact.permissions?.can_receive_case_updates ?? true,
    can_access_case: contact.permissions?.can_access_case ?? false,
    can_view_limited_case_info: contact.permissions?.can_view_limited_case_info ?? true,
    can_view_medical: contact.permissions?.can_view_medical ?? false,
    can_view_documents: contact.permissions?.can_view_documents ?? false,
  })
  const [submitting, setSubmitting] = useState(false)

  const handleToggle = (key: keyof typeof perms) => {
    setPerms(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setSubmitting(true)
      await onSave(perms)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className="bg-[#091528] text-white p-5 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white">Contact Permissions</h3>
            <p className="text-xs text-slate-300">Granular access for {contact.full_name} ({contact.relationship})</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Configure explicit permissions. Changing permissions here will be audited and immediately enforced across case tracking and communications.
          </p>

          <div className="space-y-3 pt-1">
            <label className="flex items-start justify-between gap-4 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
              <div>
                <span className="text-xs font-bold text-slate-900 block">Accident Notifications</span>
                <span className="text-[11px] text-slate-500">Allow automatic SOS and incident dispatch notifications.</span>
              </div>
              <input
                type="checkbox"
                checked={perms.can_notify_accident}
                onChange={() => handleToggle('can_notify_accident')}
                className="mt-1 rounded text-[#ff7518] focus:ring-[#ff7518]"
              />
            </label>

            <label className="flex items-start justify-between gap-4 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
              <div>
                <span className="text-xs font-bold text-slate-900 block">Receive Case Updates</span>
                <span className="text-[11px] text-slate-500">Receive milestone SMS/Email alerts on hospital and police status.</span>
              </div>
              <input
                type="checkbox"
                checked={perms.can_receive_case_updates}
                onChange={() => handleToggle('can_receive_case_updates')}
                className="mt-1 rounded text-[#ff7518] focus:ring-[#ff7518]"
              />
            </label>

            <label className="flex items-start justify-between gap-4 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
              <div>
                <span className="text-xs font-bold text-slate-900 block">Direct Case Workspace Access</span>
                <span className="text-[11px] text-slate-500">Allow this contact to log in and collaborate in your active case.</span>
              </div>
              <input
                type="checkbox"
                checked={perms.can_access_case}
                onChange={() => handleToggle('can_access_case')}
                className="mt-1 rounded text-[#ff7518] focus:ring-[#ff7518]"
              />
            </label>

            <label className="flex items-start justify-between gap-4 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
              <div>
                <span className="text-xs font-bold text-slate-900 block">Medical Info Access</span>
                <span className="text-[11px] text-slate-500">Allow contact to view blood group, allergies, and emergency medical notes.</span>
              </div>
              <input
                type="checkbox"
                checked={perms.can_view_medical}
                onChange={() => handleToggle('can_view_medical')}
                className="mt-1 rounded text-[#ff7518] focus:ring-[#ff7518]"
              />
            </label>

            <label className="flex items-start justify-between gap-4 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer">
              <div>
                <span className="text-xs font-bold text-slate-900 block">Wallet Documents Access</span>
                <span className="text-[11px] text-slate-500">Allow access to view vehicle insurance, RC, and uploaded hospital bills.</span>
              </div>
              <input
                type="checkbox"
                checked={perms.can_view_documents}
                onChange={() => handleToggle('can_view_documents')}
                className="mt-1 rounded text-[#ff7518] focus:ring-[#ff7518]"
              />
            </label>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-xl"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-md transition disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save Permissions'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
