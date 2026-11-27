import { useState, useId, type ChangeEvent } from 'react'
import type { UploadDocumentFormData, VehicleOption, CaseOption } from './types'

interface UploadDocumentWizardProps {
  vehicles: VehicleOption[]
  cases: CaseOption[]
  onCancel: () => void
  onSave: (data: UploadDocumentFormData, file: File) => Promise<void>
}

const CATEGORY_OPTIONS = [
  { id: 'personal', label: 'Personal Document', desc: 'Identity, PAN, address proofs' },
  { id: 'driving_licence', label: 'Driving Licence', desc: 'Driver credentials and endorsements' },
  { id: 'vehicle', label: 'Vehicle Document', desc: 'RC, PUC, invoice, registration' },
  { id: 'insurance', label: 'Insurance Document', desc: 'Vehicle, health & accident policies' },
  { id: 'medical', label: 'Medical Document', desc: 'Clinical reports, bills & prescriptions', sensitive: true },
  { id: 'accident_case', label: 'Accident Case Document', desc: 'Police reports, FIR, case records' },
  { id: 'other', label: 'Other Document', desc: 'General records & affidavits' },
]

const TYPE_MAPPINGS: Record<string, { id: string; label: string }[]> = {
  personal: [
    { id: 'pan', label: 'PAN Card' },
    { id: 'aadhaar', label: 'Aadhaar Card (Voluntary)' },
    { id: 'passport', label: 'Passport' },
    { id: 'voter_id', label: 'Voter ID' },
    { id: 'address_proof', label: 'Address Proof' },
    { id: 'other', label: 'Other Personal Document' },
  ],
  driving_licence: [
    { id: 'driving_licence', label: 'Driving Licence (LMV / MCWG)' },
    { id: 'commercial_dl', label: 'Commercial Driving Licence' },
    { id: 'learners_permit', label: "Learner's Driving Licence" },
    { id: 'international_dl', label: 'International Driving Permit' },
  ],
  vehicle: [
    { id: 'rc', label: 'Registration Certificate (RC)' },
    { id: 'insurance', label: 'Vehicle Insurance Policy' },
    { id: 'puc', label: 'Pollution Under Control (PUC)' },
    { id: 'purchase_invoice', label: 'Vehicle Purchase Invoice' },
    { id: 'service_record', label: 'Service Record / Warranty' },
    { id: 'other', label: 'Other Vehicle Document' },
  ],
  insurance: [
    { id: 'insurance', label: 'Comprehensive Vehicle Policy' },
    { id: 'third_party_insurance', label: 'Third-Party Liability Policy' },
    { id: 'health_insurance', label: 'Health Insurance Policy' },
    { id: 'personal_accident', label: 'Personal Accident Cover' },
    { id: 'life_insurance', label: 'Life / Term Insurance' },
    { id: 'other', label: 'Other Insurance Document' },
  ],
  medical: [
    { id: 'hospital_bill', label: 'Hospital Emergency / Inpatient Bill' },
    { id: 'medical_report', label: 'Medical Report / Clinical Summary' },
    { id: 'discharge_summary', label: 'Hospital Discharge Summary' },
    { id: 'prescription', label: 'Doctor Prescription' },
    { id: 'diagnostic_report', label: 'Diagnostic / Scan / Lab Report' },
    { id: 'other', label: 'Other Medical Record' },
  ],
  accident_case: [
    { id: 'police_complaint', label: 'Police Complaint / Intimation Copy' },
    { id: 'fir', label: 'First Information Report (FIR)' },
    { id: 'hospital_bill', label: 'Hospital Emergency Cashless Bill' },
    { id: 'medical_report', label: 'Trauma / Medico-Legal Assessment' },
    { id: 'accident_photo', label: 'Accident Scene Photo / Evidence' },
    { id: 'claim_document', label: 'PM-RAHAT / Insurance Claim Form' },
    { id: 'other', label: 'Other Case Document' },
  ],
  other: [
    { id: 'affidavit', label: 'Notarized Affidavit' },
    { id: 'legal_notice', label: 'Legal Notice / Correspondence' },
    { id: 'general', label: 'General Document' },
  ],
}

export function UploadDocumentWizard({
  vehicles,
  cases,
  onCancel,
  onSave,
}: UploadDocumentWizardProps) {
  const [step, setStep] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState('')
  const fileInputId = useId()

  const [form, setForm] = useState<UploadDocumentFormData>({
    document_name: '',
    category: 'personal',
    document_type: 'pan',
    document_number: '',
    issuing_authority: '',
    issue_date: '',
    expiry_date: '',
    resource_type: 'USER',
    resource_id: '',
    notes: '',
  })

  const [file, setFile] = useState<File | null>(null)
  const [filePreview, setFilePreview] = useState<string | null>(null)

  const steps = [
    { num: 1, title: 'Category', desc: 'Select document domain' },
    { num: 2, title: 'Document Type', desc: 'Specify document format' },
    { num: 3, title: 'Resource Link', desc: 'Associate with profile, vehicle or case' },
    { num: 4, title: 'Upload File', desc: 'PDF, JPG, PNG or WEBP' },
    { num: 5, title: 'Metadata', desc: 'Identifier, authority & validity' },
    { num: 6, title: 'Review & Save', desc: 'Confirm & save to wallet' },
  ]

  const handleCategoryChange = (cat: string) => {
    const types = TYPE_MAPPINGS[cat] || []
    let defaultResType: 'USER' | 'VEHICLE' | 'ACCIDENT_CASE' = 'USER'
    let defaultResId = ''

    if (cat === 'vehicle' && vehicles.length > 0) {
      defaultResType = 'VEHICLE'
      defaultResId = vehicles[0].id
    } else if (cat === 'accident_case' && cases.length > 0) {
      defaultResType = 'ACCIDENT_CASE'
      defaultResId = cases[0].case_id
    }

    setForm({
      ...form,
      category: cat,
      document_type: types[0]?.id || 'other',
      resource_type: defaultResType,
      resource_id: defaultResId,
    })
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return

    if (selected.size > 10 * 1024 * 1024) {
      setErr('File size exceeds maximum allowed limit of 10 MB')
      return
    }

    setErr('')
    setFile(selected)

    // Suggest default document name if not provided
    if (!form.document_name) {
      const nameWithoutExt = selected.name.replace(/\.[^/.]+$/, '').replace(/[_.-]+/g, ' ')
      setForm((prev) => ({ ...prev, document_name: nameWithoutExt }))
    }

    if (selected.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = () => setFilePreview(reader.result as string)
      reader.readAsDataURL(selected)
    } else {
      setFilePreview(null)
    }
  }

  const handleNext = () => {
    setErr('')
    if (step === 4 && !file) {
      setErr('Please select or upload a document file to proceed')
      return
    }
    if (step === 5 && !form.document_name.trim()) {
      setErr('Please enter a display name for this document')
      return
    }
    setStep((s) => Math.min(6, s + 1))
  }

  const handleSubmit = async () => {
    if (!file) {
      setErr('Please attach a document file')
      return
    }
    setSubmitting(true)
    setErr('')
    try {
      await onSave(form, file)
    } catch (e: any) {
      setErr(e.message || 'Failed to upload document')
      setSubmitting(false)
    }
  }

  const currentTypes = TYPE_MAPPINGS[form.category] || []

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 pb-16">
      {/* Wizard Header Bar */}
      <div className="bg-[#091528] text-white border-b border-[#13243d] py-6 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-400 font-medium mb-1">
              <button
                onClick={onCancel}
                className="hover:text-white transition flex items-center gap-1 cursor-pointer"
              >
                ← Back to My Documents
              </button>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Upload New Document
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Securely store and link documents to your personal profile, registered vehicle or accident case.
            </p>
          </div>
          <button
            onClick={onCancel}
            disabled={submitting}
            className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition cursor-pointer"
            title="Cancel"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Step Progress Bar */}
        <div className="bg-white rounded-2xl border border-slate-200/90 p-4 sm:p-5 shadow-sm mb-6">
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
            {steps.map((st) => {
              const isPast = st.num < step
              const isCurrent = st.num === step
              return (
                <div
                  key={st.num}
                  className={`flex flex-col p-2.5 rounded-xl border transition-all ${
                    isCurrent
                      ? 'bg-[#ebf3ff] border-[#2563eb] text-[#2563eb]'
                      : isPast
                      ? 'bg-slate-50 border-slate-200 text-slate-600'
                      : 'border-transparent text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold">
                    <span
                      className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        isCurrent
                          ? 'bg-[#2563eb] text-white'
                          : isPast
                          ? 'bg-[#16a34a] text-white'
                          : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {isPast ? '✓' : st.num}
                    </span>
                    <span className="truncate">{st.title}</span>
                  </div>
                  <span className="text-[10px] text-slate-500 mt-1 hidden sm:block truncate">
                    {st.desc}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Wizard Card */}
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 sm:p-8">
          {err && (
            <div className="mb-6 p-3.5 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-center gap-2">
              <span>⚠️</span>
              <span>{err}</span>
            </div>
          )}

          {/* STEP 1: SELECT CATEGORY */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-bold text-navy-950">Step 1: Choose Document Category</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Select the domain of the document you want to store in your wallet.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {CATEGORY_OPTIONS.map((cat) => {
                  const selected = form.category === cat.id
                  return (
                    <div
                      key={cat.id}
                      onClick={() => handleCategoryChange(cat.id)}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition flex items-start gap-3 select-none ${
                        selected
                          ? 'border-[#ff7518] bg-[#fffaf5] shadow-sm'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="doc_category"
                        checked={selected}
                        onChange={() => handleCategoryChange(cat.id)}
                        className="mt-0.5 text-[#ff7518] focus:ring-[#ff7518]"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-navy-950">{cat.label}</span>
                          {cat.sensitive && (
                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                              🔒 Sensitive
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">{cat.desc}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* STEP 2: SELECT DOCUMENT TYPE */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-bold text-navy-950">Step 2: Select Document Type</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Specify the exact classification for this document.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                {currentTypes.map((t) => {
                  const selected = form.document_type === t.id
                  return (
                    <div
                      key={t.id}
                      onClick={() => setForm({ ...form, document_type: t.id })}
                      className={`p-3.5 rounded-xl border-2 cursor-pointer transition flex items-center gap-3 select-none ${
                        selected
                          ? 'border-[#2563eb] bg-[#ebf3ff]'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="doc_type"
                        checked={selected}
                        onChange={() => setForm({ ...form, document_type: t.id })}
                        className="text-[#2563eb] focus:ring-[#2563eb]"
                      />
                      <span className="text-xs font-semibold text-navy-950">{t.label}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* STEP 3: LINK THE DOCUMENT */}
          {step === 3 && (
            <div className="space-y-5">
              <div>
                <h3 className="text-base font-bold text-navy-950">Step 3: Link Resource (Single Source of Truth)</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Associating this document makes it automatically visible across the linked vehicle, accident case or profile.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setForm({ ...form, resource_type: 'USER', resource_id: '' })}
                  className={`p-4 rounded-xl border text-left transition cursor-pointer ${
                    form.resource_type === 'USER'
                      ? 'border-[#2563eb] bg-[#ebf3ff]'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="text-base">👤</div>
                  <div className="text-xs font-bold text-navy-950 mt-1">Personal Profile</div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Associated directly with user</p>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setForm({
                      ...form,
                      resource_type: 'VEHICLE',
                      resource_id: vehicles[0]?.id || '',
                    })
                  }
                  className={`p-4 rounded-xl border text-left transition cursor-pointer ${
                    form.resource_type === 'VEHICLE'
                      ? 'border-[#2563eb] bg-[#ebf3ff]'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="text-base">🚗</div>
                  <div className="text-xs font-bold text-navy-950 mt-1">Registered Vehicle</div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Appears in My Vehicles module</p>
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setForm({
                      ...form,
                      resource_type: 'ACCIDENT_CASE',
                      resource_id: cases[0]?.case_id || '',
                    })
                  }
                  className={`p-4 rounded-xl border text-left transition cursor-pointer ${
                    form.resource_type === 'ACCIDENT_CASE'
                      ? 'border-[#2563eb] bg-[#ebf3ff]'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <div className="text-base">🚨</div>
                  <div className="text-xs font-bold text-navy-950 mt-1">Accident Case</div>
                  <p className="text-[11px] text-slate-500 mt-0.5">Appears in Case workspace</p>
                </button>
              </div>

              {/* Resource Sub-selectors */}
              {form.resource_type === 'VEHICLE' && (
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <label className="block text-xs font-bold text-navy-950">
                    Select Registered Vehicle <span className="text-red-500">*</span>
                  </label>
                  {vehicles.length > 0 ? (
                    <select
                      value={form.resource_id}
                      onChange={(e) => setForm({ ...form, resource_id: e.target.value })}
                      className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 bg-white text-navy-950 focus:ring-2 focus:ring-navy-900"
                    >
                      {vehicles.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.registration_number} — {v.manufacturer} {v.model}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-xs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                      No registered vehicles found in your account. You can register a vehicle in My Vehicles or link this document to your personal profile.
                    </p>
                  )}
                </div>
              )}

              {form.resource_type === 'ACCIDENT_CASE' && (
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <label className="block text-xs font-bold text-navy-950">
                    Select Accident Case <span className="text-red-500">*</span>
                  </label>
                  {cases.length > 0 ? (
                    <select
                      value={form.resource_id}
                      onChange={(e) => setForm({ ...form, resource_id: e.target.value })}
                      className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 bg-white text-navy-950 focus:ring-2 focus:ring-navy-900"
                    >
                      {cases.map((c) => (
                        <option key={c.case_id} value={c.case_id}>
                          {c.case_number} — {c.victim_display_name || 'Accident Case'} ({c.hospital_name || 'Hospital'})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-xs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                      No active accident cases found in your account.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* STEP 4: UPLOAD FILE */}
          {step === 4 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-bold text-navy-950">Step 4: Upload File</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Select a document file. Supported formats: PDF, PNG, JPG, JPEG, WEBP (Max 10 MB).
                </p>
              </div>

              {!file ? (
                <label 
                  htmlFor={fileInputId}
                  className="card border-2 border-dashed border-slate-300 hover:border-navy-700 hover:bg-slate-50/50 p-8 rounded-2xl flex flex-col items-center justify-center text-center cursor-pointer transition"
                >
                  <input
                    id={fileInputId}
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg,.webp"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                  <div className="h-12 w-12 rounded-full bg-[#ebf3ff] text-[#2563eb] flex items-center justify-center text-xl mb-3">
                    📁
                  </div>
                  <div className="text-sm font-bold text-navy-950">Click or drag & drop to upload</div>
                  <div className="text-xs text-slate-500 mt-1">
                    PDF, JPG, PNG or WEBP · Maximum file size 10 MB
                  </div>
                </label>
              ) : (
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    {filePreview ? (
                      <img
                        src={filePreview}
                        alt="Preview"
                        className="h-16 w-16 object-cover rounded-lg border border-slate-200"
                      />
                    ) : (
                      <div className="h-16 w-16 rounded-lg bg-red-100 text-red-700 flex flex-col items-center justify-center font-bold text-xs">
                        <span>📄</span>
                        <span className="text-[10px] uppercase">PDF</span>
                      </div>
                    )}
                    <div>
                      <div className="text-xs font-bold text-navy-950">{file.name}</div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {(file.size / 1024).toFixed(1)} KB · {file.type || 'Document'}
                      </div>
                      <span className="inline-block mt-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        ✓ File validated
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <label 
                      htmlFor={fileInputId}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 rounded-lg transition cursor-pointer"
                    >
                      Replace File
                      <input
                        id={fileInputId}
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.webp"
                        className="hidden"
                        onChange={handleFileChange}
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setFile(null)
                        setFilePreview(null)
                      }}
                      className="px-3 py-1.5 text-xs font-semibold text-red-600 bg-white border border-red-200 hover:bg-red-50 rounded-lg transition cursor-pointer"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 5: METADATA */}
          {step === 5 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-bold text-navy-950">Step 5: Document Metadata</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Add identifying metadata for search and expiry tracking. Optional fields can be left blank.
                </p>
              </div>

              <div className="space-y-3 pt-1">
                <div>
                  <label className="block text-xs font-bold text-navy-950 mb-1">
                    Document Display Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Karnataka Driving Licence"
                    value={form.document_name}
                    onChange={(e) => setForm({ ...form, document_name: e.target.value })}
                    className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Document / Policy / Registration Number
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. KA05-2020-0081928"
                      value={form.document_number}
                      onChange={(e) => setForm({ ...form, document_number: e.target.value })}
                      className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Issuing Authority / Provider
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. RTO Bengaluru South / Tata AIG"
                      value={form.issuing_authority}
                      onChange={(e) => setForm({ ...form, issuing_authority: e.target.value })}
                      className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
                      Expiry Date (if applicable)
                    </label>
                    <input
                      type="date"
                      value={form.expiry_date}
                      onChange={(e) => setForm({ ...form, expiry_date: e.target.value })}
                      className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
                    />
                    <span className="text-[10px] text-slate-400 mt-0.5 block">
                      Leave empty for documents without expiration.
                    </span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Notes & Remarks
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Optional notes or additional details..."
                    value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                    className="w-full text-xs font-medium rounded-xl border border-slate-300 p-2.5 focus:ring-2 focus:ring-navy-900"
                  />
                </div>

                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2">
                  <span className="text-sm shrink-0">🛡️</span>
                  <span className="leading-relaxed">
                    <strong>Verification Notice:</strong> Uploaded documents receive <em>Unverified</em> status by default. You can verify them with authorized external providers (DigiLocker, VAHAN, IIB) from your Document Wallet.
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* STEP 6: REVIEW & SAVE */}
          {step === 6 && (
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-bold text-navy-950">Step 6: Review Summary Before Saving</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Verify the document details below. Once confirmed, it will be added to your Document Wallet.
                </p>
              </div>

              <div className="p-5 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                  <div>
                    <div className="text-sm font-bold text-navy-950">{form.document_name}</div>
                    <div className="text-xs text-slate-500">
                      File: {file?.name} ({(file ? file.size / 1024 : 0).toFixed(1)} KB)
                    </div>
                  </div>
                  <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-[#ebf3ff] text-[#2563eb] capitalize">
                    {form.category.replace('_', ' ')}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[11px]">Classification</span>
                    <span className="font-semibold text-slate-700 capitalize">
                      {form.document_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Linked Resource</span>
                    <span className="font-semibold text-slate-700">
                      {form.resource_type === 'USER'
                        ? 'Personal Profile'
                        : form.resource_type === 'VEHICLE'
                        ? vehicles.find((v) => v.id === form.resource_id)?.registration_number || 'Vehicle'
                        : cases.find((c) => c.case_id === form.resource_id)?.case_number || 'Accident Case'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Document Number</span>
                    <span className="font-semibold text-slate-700">
                      {form.document_number || 'Not provided'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Issuing Authority</span>
                    <span className="font-semibold text-slate-700">
                      {form.issuing_authority || 'Not provided'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Issue Date</span>
                    <span className="font-semibold text-slate-700">
                      {form.issue_date || 'Not specified'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[11px]">Expiry Date</span>
                    <span className="font-semibold text-slate-700">
                      {form.expiry_date || 'Does not expire'}
                    </span>
                  </div>
                </div>

                {form.notes && (
                  <div className="pt-2 border-t border-slate-200 text-xs">
                    <span className="text-slate-400 block text-[11px]">Notes:</span>
                    <span className="text-slate-700">{form.notes}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Action Footer */}
          <div className="flex items-center justify-between pt-6 mt-6 border-t border-slate-100">
            {step > 1 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                disabled={submitting}
                className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-xl transition cursor-pointer"
              >
                ← Back
              </button>
            ) : (
              <button
                type="button"
                onClick={onCancel}
                disabled={submitting}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition cursor-pointer"
              >
                Cancel
              </button>
            )}

            {step < 6 ? (
              <button
                type="button"
                onClick={handleNext}
                className="px-5 py-2.5 rounded-full text-xs font-bold text-white bg-[#091528] hover:bg-[#13243d] transition cursor-pointer"
              >
                Continue →
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="px-6 py-2.5 rounded-full text-xs font-bold text-white bg-[#ff7518] hover:bg-[#ea6309] shadow-md shadow-[#ff7518]/20 transition cursor-pointer disabled:opacity-50"
              >
                {submitting ? 'Saving Document...' : 'Confirm & Save Document'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
