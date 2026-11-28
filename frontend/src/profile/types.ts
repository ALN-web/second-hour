export interface UserProfileData {
  user_id: string
  name: string
  role_label: string
  email: string
  email_verified: boolean
  phone: string
  phone_verified: boolean
  date_of_birth?: string | null
  gender?: string | null
  profile_photo?: string | null
  preferred_language: string
  account_status: string
  created_at: string
  updated_at: string
  stats: {
    completion_percentage: number
    missing_items: string[]
    registered_vehicles_count: number
    emergency_contacts_count: number
    verified_contacts_count: number
  }
}

export interface ContactPermissions {
  can_notify_accident: boolean
  can_receive_case_updates: boolean
  can_access_case: boolean
  permitted_case_ids: string[]
  can_view_limited_case_info: boolean
  can_view_medical: boolean
  can_view_documents: boolean
}

export interface EmergencyContactItem {
  id: string
  full_name: string
  relationship: string
  mobile_number: string
  alternate_number?: string | null
  email?: string | null
  priority: number
  is_primary: boolean
  preferred_contact_method: string
  created_at: string
  updated_at: string
  permissions: ContactPermissions
}

export interface MedicalInfoData {
  disclaimer: string
  blood_group?: string | null
  allergies?: string | null
  medical_conditions?: string | null
  medications?: string | null
  emergency_notes?: string | null
  share_with_ems: boolean
  share_with_ai: boolean
  updated_at?: string | null
}

export interface AddressItem {
  id?: string
  address_type: 'current' | 'permanent'
  address_line_1: string
  address_line_2?: string | null
  city: string
  state: string
  pin_code: string
  country: string
  is_same_as_current: boolean
  updated_at?: string | null
}

export interface IdentityDocItem {
  id: string
  document_name: string
  document_type: string
  masked_number: string
  verification_status: string
  verification_provider?: string | null
  verified_at?: string | null
  verification_reference_id?: string | null
  failure_reason?: string | null
  issuing_authority: string
  expiry_date?: string | null
  file_name: string
  file_size?: number
  uploaded_at: string
}

export interface PrivacyPreferences {
  ai_data_access_enabled: boolean
  ai_include_medical: boolean
  ai_include_documents: boolean
  ai_include_vehicles: boolean
  ai_include_cases: boolean
  allow_emergency_broadcast: boolean
  updated_at?: string | null
}

export interface NotificationPreferences {
  channels: {
    email_notifications: boolean
    sms_notifications: boolean
    in_app_notifications: boolean
    whatsapp_notifications: boolean
  }
  alerts: {
    accident_alerts: boolean
    case_updates: boolean
    document_expiry_reminders: boolean
    insurance_renewal_reminders: boolean
    pending_task_reminders: boolean
  }
  updated_at?: string | null
}

export interface SecurityOverview {
  user_id: string
  email_verified: boolean
  phone_verified: boolean
  active_sessions: {
    id: string
    device: string
    ip_masked: string
    last_active: string
    is_current: boolean
  }[]
  recent_security_activity: {
    id: number
    action: string
    details: string
    timestamp: string
  }[]
}
