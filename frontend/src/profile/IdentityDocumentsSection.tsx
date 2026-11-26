import type { IdentityDocItem } from './types'

interface IdentityDocumentsSectionProps {
  documents: IdentityDocItem[]
  onNavigateToDocuments: () => void
}

export function IdentityDocumentsSection({
  documents,
  onNavigateToDocuments,
}: IdentityDocumentsSectionProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-5 sm:p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Identity Documents</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Verified identity records linked directly from your centralized Document Wallet.
          </p>
        </div>

        <button
          onClick={onNavigateToDocuments}
          className="px-4 py-2 text-xs font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-xl transition flex items-center gap-1.5 cursor-pointer shrink-0"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
          <span>Open Document Wallet</span>
        </button>
      </div>

      {/* Security & Privacy Notice */}
      <div className="m-5 sm:m-6 p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-2.5">
        <svg className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <p className="leading-relaxed">
          <strong>Privacy Safeguard:</strong> Identity document files are preserved in the centralized Document Wallet with encryption. Masked identifiers protect sensitive numbers against unnecessary exposure.
        </p>
      </div>

      {/* Documents Grid */}
      <div className="p-5 sm:p-6 pt-0 space-y-3">
        {documents.length === 0 ? (
          <div className="text-center py-10 px-4 border border-dashed border-slate-200 rounded-2xl">
            <p className="text-xs text-slate-500">No identity documents linked yet.</p>
            <button
              onClick={onNavigateToDocuments}
              className="mt-2 text-xs font-semibold text-[#ff7518] hover:underline"
            >
              Upload Driving Licence or Identity Card
            </button>
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-100 text-sky-600 flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
                  </svg>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xs font-bold text-slate-900">{doc.document_name}</h3>
                    <span className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {doc.verification_status.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-1">
                    <span className="font-mono font-medium text-slate-800">{doc.masked_number}</span>
                    <span>·</span>
                    <span>{doc.issuing_authority}</span>
                    {doc.expiry_date && (
                      <>
                        <span>·</span>
                        <span>Expires: {doc.expiry_date}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={onNavigateToDocuments}
                className="self-end sm:self-center px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition cursor-pointer"
              >
                View in Wallet
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
