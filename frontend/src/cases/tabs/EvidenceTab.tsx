import { useState } from 'react'
import type { CaseDocumentItem } from '../types'
import { api } from '../../api'

interface EvidenceTabProps {
  caseId: string
  evidence: {
    all: CaseDocumentItem[]
    accident_photos: CaseDocumentItem[]
    injury_evidence: CaseDocumentItem[]
    supporting_docs: CaseDocumentItem[]
  }
  onRefresh: () => void
}

export function EvidenceTab({ caseId, evidence, onRefresh }: EvidenceTabProps) {
  const [activeCategory, setActiveCategory] = useState<'all' | 'photos' | 'injury' | 'documents'>('all')
  const [revealedInjuries, setRevealedInjuries] = useState<Record<string, boolean>>({})
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadType, setUploadType] = useState('accident_photo')
  const [uploadNotes, setUploadNotes] = useState('')
  const [uploading, setUploading] = useState(false)
  const [previewDoc, setPreviewDoc] = useState<CaseDocumentItem | null>(null)

  const items =
    activeCategory === 'photos'
      ? evidence.accident_photos
      : activeCategory === 'injury'
      ? evidence.injury_evidence
      : activeCategory === 'documents'
      ? evidence.supporting_docs
      : evidence.all

  const toggleReveal = (docId: string) => {
    setRevealedInjuries((prev) => ({ ...prev, [docId]: !prev[docId] }))
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uploadFile) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('document_type', uploadType)
      formData.append('category', uploadType.includes('photo') ? 'accident_case' : 'medical')
      formData.append('notes', uploadNotes)

      await api(`/api/cases/${caseId}/evidence`, {
        method: 'POST',
        form: formData,
      })

      setUploadModalOpen(false)
      setUploadFile(null)
      setUploadNotes('')
      onRefresh()
    } catch (err) {
      console.error('Failed to upload evidence:', err)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Evidence Navigation & Action Header */}
      <div className="card p-5 bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-navy-950 flex items-center gap-2">
            <span>📁</span>
            <span>Case Evidence & Supporting Documents</span>
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Synchronized with Second Hour Document Wallet without duplicating records
          </p>
        </div>

        <button
          onClick={() => setUploadModalOpen(true)}
          className="btn-accent text-xs px-4 py-2 rounded-xl font-semibold flex items-center gap-2 cursor-pointer self-start sm:self-auto shadow-xs"
        >
          <span>+</span>
          <span>Upload Evidence / Document</span>
        </button>
      </div>

      {/* Subcategory Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { id: 'all', label: `All Evidence (${evidence.all.length})` },
          { id: 'photos', label: `Accident Photos (${evidence.accident_photos.length})` },
          { id: 'injury', label: `Injury Evidence (${evidence.injury_evidence.length})` },
          { id: 'documents', label: `Case Documents (${evidence.supporting_docs.length})` },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveCategory(tab.id as any)}
            className={`px-4 py-2 text-xs font-semibold rounded-xl transition cursor-pointer whitespace-nowrap ${
              activeCategory === tab.id
                ? 'bg-navy-950 text-white shadow-xs'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Evidence Items Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((doc) => {
          const isInjury =
            doc.category === 'medical' ||
            doc.document_type.includes('injury') ||
            doc.document_type === 'medical_report'
          const isRevealed = revealedInjuries[doc.id]
          const isPdf = doc.mime_type === 'application/pdf'

          return (
            <div
              key={doc.id}
              className="card p-4 bg-white border border-slate-200 rounded-xl shadow-xs hover:border-navy-300 hover:shadow-sm transition flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="font-semibold text-slate-400 capitalize">
                    {doc.document_type.replace(/_/g, ' ')}
                  </span>
                  <span className="chip bg-slate-100 text-slate-600 font-mono text-[10px] px-2 py-0.5 rounded">
                    {(doc.file_size / 1024).toFixed(1)} KB
                  </span>
                </div>

                {/* Media Preview or Sensitive Privacy Blur */}
                {isInjury && !isRevealed ? (
                  <div className="w-full h-36 rounded-lg bg-orange-50/50 border border-orange-200 flex flex-col items-center justify-center p-4 text-center space-y-2">
                    <span className="text-xl">🔒</span>
                    <div>
                      <div className="text-xs font-bold text-orange-900">
                        Sensitive Medical Evidence
                      </div>
                      <div className="text-[11px] text-orange-700 mt-0.5">
                        Blurred to protect patient privacy and comfort
                      </div>
                    </div>
                    <button
                      onClick={() => toggleReveal(doc.id)}
                      className="text-xs font-semibold bg-white border border-orange-300 text-orange-800 px-3 py-1 rounded-lg hover:bg-orange-100/50 transition cursor-pointer"
                    >
                      Click to Reveal
                    </button>
                  </div>
                ) : (
                  <div className="w-full h-36 rounded-lg bg-slate-100 border border-slate-200 overflow-hidden flex items-center justify-center relative">
                    {isPdf ? (
                      <div className="flex flex-col items-center justify-center text-slate-500">
                        <span className="text-3xl mb-1">📄</span>
                        <span className="text-xs font-mono font-medium">{doc.file_name}</span>
                        <span className="text-[10px] text-slate-400 mt-0.5">PDF Document</span>
                      </div>
                    ) : (
                      <img
                        src={doc.download_url}
                        alt={doc.document_name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          // Fallback icon if image placeholder
                          (e.target as HTMLElement).style.display = 'none'
                        }}
                      />
                    )}
                    {isInjury && (
                      <button
                        onClick={() => toggleReveal(doc.id)}
                        className="absolute top-2 right-2 bg-black/60 text-white text-[10px] px-2 py-0.5 rounded cursor-pointer"
                      >
                        Hide
                      </button>
                    )}
                  </div>
                )}

                <h4 className="text-sm font-bold text-navy-950 mt-3 truncate">
                  {doc.document_name}
                </h4>
                {doc.notes && (
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                    {doc.notes}
                  </p>
                )}
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-[11px] text-slate-400">
                  {new Date(doc.created_at).toLocaleDateString()}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPreviewDoc(doc)}
                    className="font-semibold text-accent-500 hover:underline cursor-pointer"
                  >
                    View
                  </button>
                  <a
                    href={doc.download_url}
                    download={doc.file_name}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-navy-800 hover:underline"
                  >
                    Download
                  </a>
                </div>
              </div>
            </div>
          )
        })}

        {items.length === 0 && (
          <div className="col-span-full py-12 text-center text-xs text-slate-500 card bg-white border border-slate-200 rounded-xl">
            No evidence or documents uploaded in this category. Click "+ Upload Evidence" above.
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {uploadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-navy-950">Upload Case Evidence</h3>
              <button
                onClick={() => setUploadModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Evidence Category
                </label>
                <select
                  value={uploadType}
                  onChange={(e) => setUploadType(e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                >
                  <option value="accident_photo">Accident Scene / Vehicle Damage Photo</option>
                  <option value="injury_evidence">Medical / Injury Evidence (Restricted)</option>
                  <option value="hospital_bill">Hospital Interim / Treatment Bill</option>
                  <option value="medical_report">Clinical Summary / Medical Report</option>
                  <option value="police_document">FIR / Police General Diary Copy</option>
                  <option value="insurance_document">Motor Insurance Claim Document</option>
                  <option value="other">Other Supporting Document</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Select File (PDF or Image)
                </label>
                <input
                  type="file"
                  required
                  accept="image/*,application/pdf"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-200 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Notes / Observations
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Left front bumper deformation; photo taken at scene before tow truck arrived."
                  value={uploadNotes}
                  onChange={(e) => setUploadNotes(e.target.value)}
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(false)}
                  className="btn-ghost text-xs px-4 py-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !uploadFile}
                  className="btn-accent text-xs px-5 py-2 rounded-xl font-semibold"
                >
                  {uploading ? 'Uploading...' : 'Save to Evidence Wallet'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h4 className="text-base font-bold text-navy-950">{previewDoc.document_name}</h4>
                <span className="text-xs text-slate-400 capitalize">{previewDoc.document_type.replace(/_/g, ' ')}</span>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-auto flex items-center justify-center bg-slate-50 rounded-xl p-4 border border-slate-200 min-h-[300px]">
              {previewDoc.mime_type === 'application/pdf' ? (
                <iframe
                  src={previewDoc.download_url}
                  title={previewDoc.document_name}
                  className="w-full h-[500px] rounded-lg border-0"
                />
              ) : (
                <img
                  src={previewDoc.download_url}
                  alt={previewDoc.document_name}
                  className="max-h-[500px] max-w-full rounded-lg object-contain shadow"
                />
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
              <span className="text-slate-500">{previewDoc.notes || 'Evidence file recorded.'}</span>
              <a
                href={previewDoc.download_url}
                download={previewDoc.file_name}
                className="btn-accent text-xs px-4 py-2 rounded-xl font-semibold"
              >
                Download File
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
