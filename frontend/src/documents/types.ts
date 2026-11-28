export interface DocumentItem {
  id: string
  user_id: string
  document_name: string
  document_type: string
  category: string
  file_name: string
  mime_type: string
  file_size: number
  sha256?: string | null
  document_number?: string | null
  issuing_authority?: string | null
  issue_date?: string | null
  expiry_date?: string | null
  verification_status: 'verified' | 'unverified' | 'pending' | 'failed' | 'expiring_soon' | 'expired' | 'not_verified'
  verification_provider?: string | null
  verified_at?: string | null
  verification_reference_id?: string | null
  verification_failure_reason?: string | null
  notes?: string | null
  resource_type: 'USER' | 'VEHICLE' | 'ACCIDENT_CASE'
  resource_id?: string | null
  resource_label: string
  resource_meta?: any
  status: 'valid' | 'expiring_soon' | 'expired'
  days_left?: number | null
  download_url: string
  preview_url: string
  created_at: string
  updated_at?: string | null
}

export interface DocumentSummary {
  total: number
  valid: number
  expiring_soon: number
  expired: number
  categories: Record<string, number>
}

export interface UploadDocumentFormData {
  document_name: string
  category: string
  document_type: string
  document_number: string
  issuing_authority: string
  issue_date: string
  expiry_date: string
  resource_type: 'USER' | 'VEHICLE' | 'ACCIDENT_CASE'
  resource_id: string
  notes: string
}

export interface VehicleOption {
  id: string
  registration_number: string
  manufacturer: string
  model: string
}

export interface CaseOption {
  case_id: string
  case_number: string
  victim_display_name?: string
  hospital_name?: string
}
