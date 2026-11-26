import { useState, type FormEvent } from 'react'
import type { DocumentItem } from './types'

interface EditDocumentModalProps {
  document: DocumentItem | null
  onClose: () => void
  onSave: (docId: string, updatedData: Partial<DocumentItem>) => Promise<void>
}

export function EditDocumentModal({
  document,
  onClose,
  onSave,
}: EditDocumentModalProps) {
  if (!document) return null

  const [form, setForm] = useState({
    document_name: document.document_name,
    category: document.category,
    document_type: document.document_type,
    document_number: document.document_number || '',
    issuing_authority: document.issuing_authority || '',
    issue_date: document.issue_date ? document.issue_date.slice(0, 10) : '',
    expiry_date: document.expiry_date ? document.expiry_date.slice(0, 10) : '',
    notes: document.notes || '',
  })
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setErr('')
    try {
      await onSave(document.id, {
        document_name: form.document_name,
        category: form.category,
        document_type: form.document_type,
        document_number: form.document_number || null,
        issuing_authority: form.issuing_authority || null,
        issue_date: form.issue_date || null,
        expiry_date: form.expiry_date || null,
        notes: form.notes || null,
      })
      onClose()
    } catch (e: any) {
      setErr(e.message || 'Failed to update document')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#091528]/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className="bg-[#091528] text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">✏️</span>
            <div>
              <h3 className="text-base font-bold text-white">Edit Document Information</h3>
              <p className="text-xs text-slate-400">Update metadata, identifiers and validity dates</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {err && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
              {err}
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-navy-950 mb-1">
              Document Display Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={form.document_name}
              onChange={(e) => setForm({ ...form, document_name: e.target.value })}
              className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Category
              </label>
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 bg-white focus:ring-2 focus:ring-navy-900"
              >
                <option value="personal">Personal Document</option>
                <option value="driving_licence">Driving Licence</option>
                <option value="vehicle">Vehicle Document</option>
                <option value="insurance">Insurance Document</option>
                <option value="medical">Medical Document</option>
                <option value="accident_case">Accident Case Document</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Document Number
              </label>
              <input
                type="text"
                placeholder="e.g. DL / Policy No"
                value={form.document_number}
                onChange={(e) => setForm({ ...form, document_number: e.target.value })}
                className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Issuing Authority / Company
            </label>
            <input
              type="text"
              placeholder="e.g. RTO / Tata AIG / Hospital"
              value={form.issuing_authority}
              onChange={(e) => setForm({ ...form, issuing_authority: e.target.value })}
              className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Issue Date
              </label>
              <input
                type="date"
                value={form.issue_date}
                onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
                className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Expiry Date
              </label>
              <input
                type="date"
                value={form.expiry_date}
                onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
                className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
              />
              <span className="text-[10px] text-slate-400 mt-0.5 block">
                Clear to remove expiry.
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Notes
            </label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 text-xs font-bold text-white bg-[#091528] hover:bg-[#13243d] rounded-xl transition cursor-pointer disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
