import { useState, type ChangeEvent } from 'react'
import type { VehicleFormData } from './types'

interface AddVehicleWizardProps {
  onCancel: () => void
  onSave: (data: VehicleFormData, photoFile: File | null, docFiles: { type: string; file: File }[]) => Promise<void>
}

export function AddVehicleWizard({ onCancel, onSave }: AddVehicleWizardProps) {
  const [step, setStep] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [err, setErr] = useState('')

  // Form state
  const [form, setForm] = useState<VehicleFormData>({
    registration_number: '',
    category: 'Four Wheeler',
    manufacturer: '',
    model: '',
    variant: '',
    manufacturing_year: new Date().getFullYear(),
    fuel_type: 'Petrol',
    color: '',
    chassis_number: '',
    engine_number: '',
    vin: '',
    engine_capacity: '',
    transmission: 'Manual',
    owner_name: 'Priya Sharma',
    ownership_type: 'Individual',
    relationship_to_user: 'Self',
    insurance: {
      provider: '',
      policy_number: '',
      policy_type: 'Comprehensive',
      start_date: '',
      expiry_date: '',
    },
  })

  // Photo & Document uploads
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [rcFile, setRcFile] = useState<File | null>(null)
  const [pucFile, setPucFile] = useState<File | null>(null)
  const [insuranceFile, setInsuranceFile] = useState<File | null>(null)

  const steps = [
    { num: 1, title: 'Basic Information', desc: 'Make, model, registration' },
    { num: 2, title: 'Technical Specs', desc: 'Engine, chassis, transmission' },
    { num: 3, title: 'Ownership', desc: 'Registered owner & relations' },
    { num: 4, title: 'Insurance Policy', desc: 'Provider, policy number & dates' },
    { num: 5, title: 'Photograph', desc: 'Main vehicle image' },
    { num: 6, title: 'Summary & Save', desc: 'Review & documents' },
  ]

  const handlePhotoSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0]
      setPhotoFile(f)
      const reader = new FileReader()
      reader.onload = (event) => {
        setPhotoPreview(event.target?.result as string)
      }
      reader.readAsDataURL(f)
    }
  }

  const handleNext = () => {
    setErr('')
    if (step === 1) {
      if (!form.registration_number.trim()) {
        setErr('Please enter the vehicle registration number.')
        return
      }
      if (!form.manufacturer.trim()) {
        setErr('Please enter the manufacturer.')
        return
      }
      if (!form.model.trim()) {
        setErr('Please enter the model.')
        return
      }
    }
    setStep((s) => Math.min(s + 1, 6))
  }

  const handleBack = () => {
    setErr('')
    setStep((s) => Math.max(s - 1, 1))
  }

  const handleFinalSubmit = async () => {
    setSubmitting(true)
    setErr('')
    try {
      const docFiles: { type: string; file: File }[] = []
      if (rcFile) docFiles.push({ type: 'rc', file: rcFile })
      if (pucFile) docFiles.push({ type: 'puc', file: pucFile })
      if (insuranceFile) docFiles.push({ type: 'insurance', file: insuranceFile })

      await onSave(form, photoFile, docFiles)
    } catch (e: any) {
      setErr(e.message || 'Failed to register vehicle')
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      {/* Header & Breadcrumb */}
      <div className="mb-6">
        <nav className="flex items-center gap-2 text-xs text-slate-500 mb-2">
          <button onClick={onCancel} className="hover:text-navy-950 font-medium transition cursor-pointer">
            Home
          </button>
          <span>/</span>
          <button onClick={onCancel} className="hover:text-navy-950 font-medium transition cursor-pointer">
            My Vehicles
          </button>
          <span>/</span>
          <span className="text-slate-800 font-semibold">Register New Vehicle</span>
        </nav>

        <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-950 tracking-tight">
          Register New Vehicle
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          Complete the vehicle profile to enable automatic PM-RAHAT readiness and insurance tracking.
        </p>
      </div>

      {/* Multi-Step Horizontal Progress Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 sm:p-5 mb-8">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {steps.map((st) => (
            <div
              key={st.num}
              onClick={() => st.num < step && setStep(st.num)}
              className={`flex items-center gap-2 p-2 rounded-xl transition ${
                step === st.num
                  ? 'bg-navy-950 text-white shadow-sm'
                  : st.num < step
                  ? 'bg-emerald-50 text-emerald-800 cursor-pointer hover:bg-emerald-100'
                  : 'text-slate-400'
              }`}
            >
              <div
                className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                  step === st.num
                    ? 'bg-[#ff7518] text-white'
                    : st.num < step
                    ? 'bg-emerald-500 text-white'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {st.num < step ? '✓' : st.num}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold truncate leading-tight">{st.title}</div>
                <div className="text-[10px] opacity-75 truncate hidden sm:block">{st.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main Wizard Form Container */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 sm:p-8">
        {err && (
          <div className="mb-6 p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
            <span>⚠️</span>
            <span>{err}</span>
          </div>
        )}

        {/* STEP 1: Basic Vehicle Information */}
        {step === 1 && (
          <div className="space-y-5 animate-fade-in">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-lg font-bold text-navy-950">Step 1: Basic Vehicle Information</h2>
              <p className="text-xs text-slate-500">Essential identifiers found on your Registration Certificate (RC).</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Registration Number <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. KA-01-MJ-2024"
                  value={form.registration_number}
                  onChange={(e) => setForm({ ...form, registration_number: e.target.value.toUpperCase() })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm font-mono font-bold tracking-wider focus:outline-none focus:ring-2 focus:ring-navy-800 uppercase"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Vehicle Category <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 bg-white"
                >
                  <option value="Four Wheeler">Four Wheeler (Car / SUV)</option>
                  <option value="Two Wheeler">Two Wheeler (Motorcycle / Scooter)</option>
                  <option value="Commercial">Commercial / Goods Carrier</option>
                  <option value="Other">Other Category</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Manufacturer (Make) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. Honda, Hyundai, Tata"
                  value={form.manufacturer}
                  onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Model <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. City, Creta, Nexon"
                  value={form.model}
                  onChange={(e) => setForm({ ...form, model: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Variant / Trim (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. ZX CVT, Dark Edition"
                  value={form.variant || ''}
                  onChange={(e) => setForm({ ...form, variant: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Manufacturing Year
                </label>
                <input
                  type="number"
                  min="1990"
                  max="2030"
                  value={form.manufacturing_year || ''}
                  onChange={(e) => setForm({ ...form, manufacturing_year: parseInt(e.target.value) || undefined })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Fuel Type
                </label>
                <select
                  value={form.fuel_type}
                  onChange={(e) => setForm({ ...form, fuel_type: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 bg-white"
                >
                  <option value="Petrol">Petrol</option>
                  <option value="Diesel">Diesel</option>
                  <option value="Electric">Electric (EV)</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="CNG">CNG / LPG</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Exterior Color
                </label>
                <input
                  type="text"
                  placeholder="e.g. Platinum White Pearl, Obsidian Black"
                  value={form.color || ''}
                  onChange={(e) => setForm({ ...form, color: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Technical Specifications */}
        {step === 2 && (
          <div className="space-y-5 animate-fade-in">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-lg font-bold text-navy-950">Step 2: Technical Information</h2>
              <p className="text-xs text-slate-500">Chassis, engine numbers and powertrain specs (optional but recommended).</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Chassis Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. MAKGM2657HM019284"
                  value={form.chassis_number || ''}
                  onChange={(e) => setForm({ ...form, chassis_number: e.target.value.toUpperCase() })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Engine Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. L15Z19827364"
                  value={form.engine_number || ''}
                  onChange={(e) => setForm({ ...form, engine_number: e.target.value.toUpperCase() })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Vehicle Identification Number (VIN)
                </label>
                <input
                  type="text"
                  placeholder="17-character VIN"
                  value={form.vin || ''}
                  onChange={(e) => setForm({ ...form, vin: e.target.value.toUpperCase() })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm font-mono uppercase focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Engine Displacement / Capacity
                </label>
                <input
                  type="text"
                  placeholder="e.g. 1498 cc, 1.5L Turbo"
                  value={form.engine_capacity || ''}
                  onChange={(e) => setForm({ ...form, engine_capacity: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Transmission Type
                </label>
                <select
                  value={form.transmission || 'Manual'}
                  onChange={(e) => setForm({ ...form, transmission: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 bg-white"
                >
                  <option value="Manual">Manual</option>
                  <option value="Automatic">Automatic (AT / Torque Converter)</option>
                  <option value="CVT">CVT (Continuously Variable)</option>
                  <option value="DCT">DCT / DSG (Dual Clutch)</option>
                  <option value="EV Direct">Single-Speed Electric Drive</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Ownership Information */}
        {step === 3 && (
          <div className="space-y-5 animate-fade-in">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-lg font-bold text-navy-950">Step 3: Ownership Details</h2>
              <p className="text-xs text-slate-500">Specify who owns the vehicle and their relation to your Second Hour profile.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Registered Owner Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Priya Sharma"
                  value={form.owner_name || ''}
                  onChange={(e) => setForm({ ...form, owner_name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Ownership Type
                </label>
                <select
                  value={form.ownership_type || 'Individual'}
                  onChange={(e) => setForm({ ...form, ownership_type: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 bg-white"
                >
                  <option value="Individual">Individual (First Owner)</option>
                  <option value="Individual (Second Owner)">Individual (Second Owner)</option>
                  <option value="Company Owned">Company / Corporate Owned</option>
                  <option value="Leased">Leased / Financed</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Relationship to Registered User
                </label>
                <select
                  value={form.relationship_to_user || 'Self'}
                  onChange={(e) => setForm({ ...form, relationship_to_user: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 bg-white"
                >
                  <option value="Self">Self (Registered User)</option>
                  <option value="Spouse">Spouse</option>
                  <option value="Parent">Parent</option>
                  <option value="Sibling">Sibling</option>
                  <option value="Child">Child</option>
                  <option value="Other">Other / Extended Family</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Insurance Information */}
        {step === 4 && (
          <div className="space-y-5 animate-fade-in">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-lg font-bold text-navy-950">Step 4: Insurance Information</h2>
              <p className="text-xs text-slate-500">Keep your policy details ready for hospital cashless and third-party assistance.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Insurance Provider
                </label>
                <input
                  type="text"
                  placeholder="e.g. Tata AIG, HDFC ERGO, ICICI Lombard"
                  value={form.insurance?.provider || ''}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      insurance: { ...form.insurance!, provider: e.target.value },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Policy Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. POL-99283401-2026"
                  value={form.insurance?.policy_number || ''}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      insurance: { ...form.insurance!, policy_number: e.target.value },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Policy Type
                </label>
                <select
                  value={form.insurance?.policy_type || 'Comprehensive'}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      insurance: { ...form.insurance!, policy_type: e.target.value },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800 bg-white"
                >
                  <option value="Comprehensive">Comprehensive (Own Damage + Third Party)</option>
                  <option value="Third Party Only">Third Party Only</option>
                  <option value="Zero Depreciation">Zero Depreciation Add-on Package</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Policy Expiry Date
                </label>
                <input
                  type="date"
                  value={form.insurance?.expiry_date ? form.insurance.expiry_date.slice(0, 10) : ''}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      insurance: { ...form.insurance!, expiry_date: e.target.value ? new Date(e.target.value).toISOString() : '' },
                    })
                  }
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-navy-800"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Attach Policy Document (PDF or Photo)
                </label>
                <input
                  type="file"
                  accept=".pdf,image/png,image/jpeg,image/webp"
                  onChange={(e) => e.target.files && setInsuranceFile(e.target.files[0])}
                  className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-navy-950 hover:file:bg-slate-200 cursor-pointer"
                />
                {insuranceFile && (
                  <div className="mt-1 text-xs text-emerald-700 font-medium">
                    ✓ Attached: {insuranceFile.name} ({(insuranceFile.size / 1024).toFixed(1)} KB)
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* STEP 5: Vehicle Photograph */}
        {step === 5 && (
          <div className="space-y-5 animate-fade-in">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-lg font-bold text-navy-950">Step 5: Main Vehicle Photograph</h2>
              <p className="text-xs text-slate-500">Upload a clear photo of your vehicle (supports JPG, PNG, WEBP).</p>
            </div>

            <div className="space-y-4">
              {photoPreview ? (
                <div className="relative rounded-2xl overflow-hidden border border-slate-200 max-w-lg mx-auto shadow-sm">
                  <img src={photoPreview} alt="Vehicle preview" className="w-full h-64 object-cover" />
                  <div className="absolute bottom-3 right-3 flex items-center gap-2">
                    <label className="px-3 py-1.5 rounded-xl bg-white/90 text-navy-900 font-semibold text-xs backdrop-blur-sm cursor-pointer shadow hover:bg-white transition">
                      Replace Photo
                      <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handlePhotoSelect} className="hidden" />
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setPhotoFile(null)
                        setPhotoPreview(null)
                      }}
                      className="px-3 py-1.5 rounded-xl bg-red-600/90 text-white font-semibold text-xs backdrop-blur-sm shadow hover:bg-red-700 transition"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-slate-300 rounded-2xl hover:border-navy-700 hover:bg-slate-50/50 cursor-pointer transition">
                  <div className="h-16 w-16 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center text-3xl mb-3">
                    📸
                  </div>
                  <span className="text-sm font-bold text-navy-950">Upload Main Vehicle Photo</span>
                  <span className="text-xs text-slate-500 mt-1">JPEG, PNG or WEBP up to 10MB</span>
                  <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handlePhotoSelect} className="hidden" />
                </label>
              )}
            </div>
          </div>
        )}

        {/* STEP 6: Document Upload & Summary Review */}
        {step === 6 && (
          <div className="space-y-6 animate-fade-in">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-lg font-bold text-navy-950">Step 6: Review & Final Documents</h2>
              <p className="text-xs text-slate-500">Review your vehicle specifications and attach optional RC or PUC certificates.</p>
            </div>

            {/* Optional RC / PUC Uploads */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Registration Certificate (RC Document)
                </label>
                <input
                  type="file"
                  accept=".pdf,image/png,image/jpeg,image/webp"
                  onChange={(e) => e.target.files && setRcFile(e.target.files[0])}
                  className="w-full text-xs text-slate-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-white file:text-navy-950 hover:file:bg-slate-100 cursor-pointer"
                />
                {rcFile && <span className="text-xs text-emerald-700 font-medium">✓ {rcFile.name}</span>}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Pollution Under Control (PUC Certificate)
                </label>
                <input
                  type="file"
                  accept=".pdf,image/png,image/jpeg,image/webp"
                  onChange={(e) => e.target.files && setPucFile(e.target.files[0])}
                  className="w-full text-xs text-slate-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-white file:text-navy-950 hover:file:bg-slate-100 cursor-pointer"
                />
                {pucFile && <span className="text-xs text-emerald-700 font-medium">✓ {pucFile.name}</span>}
              </div>
            </div>

            {/* Registration Summary Card */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div>
                  <span className="font-mono text-sm font-bold bg-navy-950 text-white px-2.5 py-1 rounded-lg">
                    {form.registration_number || 'REG-PENDING'}
                  </span>
                  <h3 className="text-base font-bold text-navy-950 mt-1">
                    {form.manufacturer} {form.model} {form.variant}
                  </h3>
                </div>
                <span className="chip bg-blue-50 text-blue-700 font-semibold">{form.category}</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">Manufacturing Year:</span>
                  <span className="font-semibold text-slate-800">{form.manufacturing_year || '-'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Fuel Type:</span>
                  <span className="font-semibold text-slate-800">{form.fuel_type}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Exterior Color:</span>
                  <span className="font-semibold text-slate-800">{form.color || 'Not specified'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Owner Name:</span>
                  <span className="font-semibold text-slate-800">{form.owner_name} ({form.relationship_to_user})</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Insurance Provider:</span>
                  <span className="font-semibold text-slate-800">{form.insurance?.provider || 'None entered'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Policy Number:</span>
                  <span className="font-semibold text-slate-800">{form.insurance?.policy_number || 'None entered'}</span>
                </div>
              </div>

              {photoPreview && (
                <div className="pt-2 flex items-center gap-3">
                  <img src={photoPreview} alt="Thumb" className="h-14 w-20 object-cover rounded-lg border border-slate-200" />
                  <span className="text-xs text-slate-600 font-medium">Main photograph attached</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Wizard Controls */}
        <div className="mt-8 pt-5 border-t border-slate-100 flex items-center justify-between">
          <button
            type="button"
            onClick={step === 1 ? onCancel : handleBack}
            disabled={submitting}
            className="px-5 py-2.5 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition cursor-pointer"
          >
            {step === 1 ? 'Cancel' : '← Back'}
          </button>

          {step < 6 ? (
            <button
              type="button"
              onClick={handleNext}
              className="px-6 py-2.5 rounded-xl text-xs font-semibold bg-navy-950 text-white hover:bg-navy-900 shadow transition cursor-pointer"
            >
              Next Step →
            </button>
          ) : (
            <button
              type="button"
              onClick={handleFinalSubmit}
              disabled={submitting}
              className="px-6 py-2.5 rounded-xl text-xs font-semibold bg-[#ff7518] text-white hover:bg-[#ea6309] shadow-md shadow-orange-500/20 transition cursor-pointer disabled:opacity-50"
            >
              {submitting ? 'Saving Vehicle…' : '✓ Save Vehicle'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
