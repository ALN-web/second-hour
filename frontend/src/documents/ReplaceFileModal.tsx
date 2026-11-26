import { useState, useId, type ChangeEvent, type FormEvent } from 'react'
import type { DocumentItem } from './types'

interface ReplaceFileModalProps {
  document: DocumentItem | null
  onClose: () => void
  onReplace: (docId: string, newFile: File) => Promise<void>
}

export function ReplaceFileModal({
  document,
  onClose,
  onReplace,
}: ReplaceFileModalProps) {
  if (!document) return null

  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [err, setErr] = useState('')
  const fileInputId = useId()

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return

    if (selected.size > 10 * 1024 * 1024) {
      setErr('File size exceeds maximum allowed limit of 10 MB')
      return
    }

    setErr('')
    setFile(selected)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) {
      setErr('Please select a replacement file')
      return
    }
    setUploading(true)
    setErr('')
    try {
      await onReplace(document.id, file)
      onClose()
    } catch (e: any) {
      setErr(e.message || 'Failed to replace file')
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#091528]/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
        <div className="bg-[#091528] text-white p-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">🔄</span>
            <div>
              <h3 className="text-base font-bold text-white">Replace Document File</h3>
              <p className="text-xs text-slate-400">Updates file while preserving metadata</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white hover:bg-white/10 rounded-lg transition cursor-pointer"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {err && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
              {err}
            </div>
          )}

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
            <div className="text-slate-400 font-semibold text-[10px] uppercase">Current File</div>
            <div className="font-bold text-navy-950 mt-0.5">{document.file_name}</div>
            <div className="text-[11px] text-slate-500">
              {(document.file_size / 1024).toFixed(1)} KB · {document.mime_type}
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-navy-950 mb-2">
              Select New File (PDF, PNG, JPG, JPEG, WEBP)
            </label>
            <label
              htmlFor={fileInputId}
              className="card border-2 border-dashed border-slate-300 hover:border-navy-700 p-6 rounded-2xl flex flex-col items-center justify-center text-center cursor-pointer transition bg-slate-50/50"
            >
              <input
                id={fileInputId}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                className="hidden"
                onChange={handleFileChange}
              />
              <span className="text-3xl mb-1">📁</span>
              <span className="text-xs font-bold text-navy-950">
                {file ? file.name : 'Click to select new replacement file'}
              </span>
              <span className="text-[10px] text-slate-400 mt-1">
                {file ? `${(file.size / 1024).toFixed(1)} KB` : 'Maximum file size 10 MB'}
              </span>
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={uploading}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={uploading || !file}
              className="px-5 py-2.5 text-xs font-bold text-white bg-[#ff7518] hover:bg-[#ea6309] rounded-xl transition cursor-pointer disabled:opacity-50 shadow-sm"
            >
              {uploading ? 'Replacing...' : 'Upload & Replace'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
