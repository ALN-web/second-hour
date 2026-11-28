import { useState } from 'react'
import type { DocumentItem } from './types'

interface DocumentViewerModalProps {
  document: DocumentItem | null
  onClose: () => void
  onEdit: (doc: DocumentItem) => void
  onReplaceFile: (doc: DocumentItem) => void
  onDelete: (docId: string) => void
}

export function DocumentViewerModal({
  document,
  onClose,
  onEdit,
  onReplaceFile,
  onDelete,
}: DocumentViewerModalProps) {
  const [zoom, setZoom] = useState(1)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)

  if (!document) return null

  const isPdf = document.mime_type === 'application/pdf' || document.file_name.toLowerCase().endsWith('.pdf')
  const isImage = document.mime_type.startsWith('image/') || /\.(jpg|jpeg|png|webp)$/i.test(document.file_name)

  const statusBg =
    document.status === 'valid'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : document.status === 'expiring_soon'
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-red-50 text-red-700 border-red-200'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-[#091528]/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-5xl h-[92vh] max-h-[850px] rounded-2xl bg-white border border-slate-200 shadow-2xl flex flex-col overflow-hidden">
        
        {/* Header Bar */}
        <div className="bg-[#091528] text-white px-5 py-3.5 flex items-center justify-between border-b border-[#13243d] flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0 pr-4">
            <div className="h-9 w-9 rounded-xl bg-white/10 flex items-center justify-center text-lg flex-shrink-0">
              {isPdf ? '📄' : isImage ? '🖼️' : '📁'}
            </div>
            <div className="min-w-0">
              <h3 className="text-sm sm:text-base font-bold text-white truncate">
                {document.document_name}
              </h3>
              <p className="text-[11px] text-slate-300 truncate">
                {document.file_name} · {(document.file_size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <a
              href={`${document.download_url}?download=true`}
              download={document.file_name}
              className="px-3 py-1.5 rounded-lg bg-[#ff7518] hover:bg-[#ea6309] text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-sm cursor-pointer"
            >
              <span>⬇</span>
              <span className="hidden sm:inline">Download</span>
            </a>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition cursor-pointer"
              title="Close Preview"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content Body: Split View */}
        <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
          
          {/* Left / Center Preview Pane (65%) */}
          <div className="flex-1 bg-slate-900 relative flex flex-col items-center justify-center p-2 sm:p-4 min-h-[250px] overflow-hidden">
            {isPdf ? (
              <div className="w-full h-full rounded-xl overflow-hidden bg-white shadow-inner flex flex-col">
                <object
                  data={`${document.preview_url}#toolbar=1&navpanes=0`}
                  type="application/pdf"
                  className="w-full h-full rounded-xl"
                >
                  <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center text-slate-600 space-y-3">
                    <span className="text-4xl">📄</span>
                    <div className="text-sm font-semibold">PDF preview not supported in this frame</div>
                    <a
                      href={`${document.download_url}?download=true`}
                      className="btn-accent text-xs"
                    >
                      Download PDF Document
                    </a>
                  </div>
                </object>
              </div>
            ) : isImage ? (
              <div className="w-full h-full flex items-center justify-center overflow-auto p-4">
                <img
                  src={document.preview_url}
                  alt={document.document_name}
                  style={{ transform: `scale(${zoom})`, transition: 'transform 0.2s' }}
                  className="max-h-full max-w-full object-contain rounded-lg shadow-xl"
                />
                {/* Floating Zoom Controls for Image */}
                <div className="absolute bottom-4 right-4 bg-navy-950/80 backdrop-blur-md rounded-xl p-1.5 flex items-center gap-2 text-white text-xs border border-white/20">
                  <button
                    onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
                    className="p-1 hover:bg-white/20 rounded"
                    title="Zoom Out"
                  >
                    -
                  </button>
                  <span className="font-mono text-[11px] px-1">{Math.round(zoom * 100)}%</span>
                  <button
                    onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
                    className="p-1 hover:bg-white/20 rounded"
                    title="Zoom In"
                  >
                    +
                  </button>
                  <button
                    onClick={() => setZoom(1)}
                    className="p-1 text-[10px] hover:bg-white/20 rounded"
                    title="Reset Zoom"
                  >
                    Reset
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center p-6 text-slate-400 space-y-3 text-center">
                <span className="text-4xl">📁</span>
                <div className="text-sm font-medium text-slate-300">File Preview Not Available</div>
                <p className="text-xs text-slate-500 max-w-xs">
                  This file format does not support inline rendering. You can securely download the file to inspect it.
                </p>
                <a
                  href={`${document.download_url}?download=true`}
                  className="btn-accent text-xs"
                >
                  Download File
                </a>
              </div>
            )}
          </div>

          {/* Right Sidebar: Details & Actions (35%) */}
          <div className="w-full lg:w-80 xl:w-96 bg-white border-t lg:border-t-0 lg:border-l border-slate-200 p-5 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-4">
              {/* Document Status Banner */}
              <div className={`p-3 rounded-xl border flex items-center justify-between text-xs font-semibold ${statusBg}`}>
                <div className="flex items-center gap-2">
                  <span>{document.status === 'valid' ? '✓' : document.status === 'expiring_soon' ? '⚠️' : '🚨'}</span>
                  <span className="capitalize">{document.status.replace('_', ' ')}</span>
                </div>
                {document.days_left !== null && document.days_left !== undefined && (
                  <span className="text-[11px]">
                    {document.days_left < 0
                      ? `Expired ${Math.abs(document.days_left)} days ago`
                      : document.days_left <= 30
                      ? `${document.days_left} days left`
                      : `Expires in ${document.days_left} days`}
                  </span>
                )}
              </div>

              {/* Resource Association Card */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                  Associated Resource
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-base">
                    {document.resource_type === 'VEHICLE'
                      ? '🚗'
                      : document.resource_type === 'ACCIDENT_CASE'
                      ? '🚨'
                      : '👤'}
                  </span>
                  <div>
                    <div className="text-xs font-bold text-navy-950">{document.resource_label}</div>
                    <div className="text-[10px] text-slate-500">
                      Single source of truth · Visible in both modules
                    </div>
                  </div>
                </div>
              </div>

              {/* Metadata Fields */}
              <div className="space-y-2.5 text-xs">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                    Category & Classification
                  </span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="font-semibold text-slate-800 capitalize">
                      {document.category.replace('_', ' ')}
                    </span>
                    <span className="text-slate-400">/</span>
                    <span className="text-slate-600 capitalize">
                      {document.document_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                    Verification State
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    {document.verification_status === 'verified' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        ✓ Verified {document.verification_provider ? `via ${document.verification_provider}` : ''}
                      </span>
                    ) : document.verification_status === 'failed' ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200">
                        ✗ Failed Verification
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                        Unverified Document
                      </span>
                    )}
                  </div>
                  {document.verification_reference_id && (
                    <span className="text-[10px] font-mono text-slate-500 block mt-0.5">
                      Ref: {document.verification_reference_id}
                    </span>
                  )}
                  {document.verification_failure_reason && (
                    <p className="text-[11px] text-red-600 mt-1">
                      Reason: {document.verification_failure_reason}
                    </p>
                  )}
                </div>

                {document.document_number && (
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                      Document / Policy Number
                    </span>
                    <span className="font-mono font-semibold text-slate-800">
                      {document.document_number}
                    </span>
                  </div>
                )}

                {document.issuing_authority && (
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                      Issuing Authority
                    </span>
                    <span className="font-semibold text-slate-800">
                      {document.issuing_authority}
                    </span>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 pt-1 border-t border-slate-100">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                      Issue Date
                    </span>
                    <span className="font-medium text-slate-700">
                      {document.issue_date ? new Date(document.issue_date).toLocaleDateString('en-IN') : '—'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                      Expiry Date
                    </span>
                    <span className="font-medium text-slate-700">
                      {document.expiry_date
                        ? new Date(document.expiry_date).toLocaleDateString('en-IN')
                        : 'No Expiry'}
                    </span>
                  </div>
                </div>

                <div className="pt-1 border-t border-slate-100">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                    Upload Timestamp
                  </span>
                  <span className="text-[11px] text-slate-600">
                    {new Date(document.created_at).toLocaleString('en-IN')}
                  </span>
                </div>

                {document.notes && (
                  <div className="pt-1 border-t border-slate-100">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">
                      Notes
                    </span>
                    <p className="text-xs text-slate-600 italic mt-0.5">{document.notes}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="pt-4 border-t border-slate-200 space-y-2 mt-4">
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => onEdit(document)}
                  className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <span>✏️</span>
                  <span>Edit Info</span>
                </button>
                <button
                  type="button"
                  onClick={() => onReplaceFile(document)}
                  className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <span>🔄</span>
                  <span>Replace File</span>
                </button>
              </div>

              {!deleteConfirmOpen ? (
                <button
                  type="button"
                  onClick={() => setDeleteConfirmOpen(true)}
                  className="w-full px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 rounded-xl transition flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <span>🗑</span>
                  <span>Delete Document</span>
                </button>
              ) : (
                <div className="p-3 bg-red-50 rounded-xl border border-red-200 text-center space-y-2 animate-fade-in">
                  <p className="text-xs font-bold text-red-700">Delete this document?</p>
                  <p className="text-[10px] text-red-600">
                    {document.resource_type !== 'USER'
                      ? 'Note: This document is linked to an active vehicle or case.'
                      : 'This action will remove it from your document wallet.'}
                  </p>
                  <div className="flex items-center justify-center gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setDeleteConfirmOpen(false)}
                      className="px-3 py-1 text-xs font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onDelete(document.id)
                        onClose()
                      }}
                      className="px-3 py-1 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-sm cursor-pointer"
                    >
                      Confirm Delete
                    </button>
                  </div>
                </div>
              )}
            </div>

          </div>

        </div>

      </div>
    </div>
  )
}
