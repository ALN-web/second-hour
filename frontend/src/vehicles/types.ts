export interface VehicleInsurance {
  id?: string | null
  provider: string | null
  policy_number: string | null
  policy_type: string | null
  start_date?: string | null
  expiry_date: string | null
  document_id?: string | null
  status: 'active' | 'expiring_soon' | 'expired' | 'not_provided'
  days_left: number | null
}

export interface VehiclePhoto {
  id: string
  photo_category: 'main' | 'front' | 'rear' | 'left' | 'right' | 'additional'
  file_name: string
  mime_type: string
  is_primary: boolean
  uploaded_at: string
  url: string
}

export interface VehicleDocument {
  id: string
  document_type: 'rc' | 'insurance' | 'puc' | 'purchase_invoice' | 'service_record' | 'other'
  document_name: string
  file_name: string
  file_size: number
  mime_type: string
  expiry_date: string | null
  verification_status: 'verified' | 'expiring_soon' | 'expired' | 'pending'
  uploaded_at: string
  url: string
}

export interface VehicleSummary {
  id: string
  registration_number: string
  category: string
  manufacturer: string
  model: string
  variant?: string | null
  manufacturing_year?: number | null
  fuel_type: string
  color?: string | null
  main_image?: string | null
  owner_name?: string | null
  ownership_type: string
  insurance: VehicleInsurance
  doc_count: number
  photo_count: number
  created_at: string
  updated_at: string
}

export interface VehicleDetail extends VehicleSummary {
  user_id: string
  chassis_number?: string | null
  engine_number?: string | null
  vin?: string | null
  engine_capacity?: string | null
  transmission?: string | null
  relationship_to_user?: string | null
  photos: VehiclePhoto[]
  documents: VehicleDocument[]
}

export interface VehicleFormData {
  registration_number: string
  category: string
  manufacturer: string
  model: string
  variant?: string
  manufacturing_year?: number
  fuel_type: string
  color?: string
  chassis_number?: string
  engine_number?: string
  vin?: string
  engine_capacity?: string
  transmission?: string
  owner_name?: string
  ownership_type?: string
  relationship_to_user?: string
  main_image?: string
  insurance?: {
    provider: string
    policy_number: string
    policy_type: string
    start_date?: string
    expiry_date?: string
  }
}
