export interface CaseSummaryMetrics {
  total_cases: number
  active_cases: number
  resolved_cases: number
  pending_actions: number
}

export interface LinkedVehicleSummary {
  vehicle_id: string
  registration_number: string
  manufacturer: string
  model: string
  variant?: string
  manufacturing_year?: number
  color?: string
  photo_url?: string
}

export interface CaseOverviewItem {
  case_id: string
  case_number: string
  status: string
  created_at: string
  incident_at: string
  approximate_location: string
  victim_display_name?: string
  victim_relationship?: string
  hospital_name?: string
  injury_severity: string
  damage_severity: string
  police_stage: string
  police_draft_status: string
  pmrahat_stage: string
  insurance_stage: string
  hospital_treatment_status: string
  pending_actions_count: number
  open_tasks_count: number
  vehicle?: LinkedVehicleSummary
}

export interface CasesOverviewResponse {
  summary: CaseSummaryMetrics
  cases: CaseOverviewItem[]
}

export interface ProgressCard {
  stage: string
  title: string
  subtitle: string
  status: 'active' | 'in_progress' | 'completed' | 'pending_review'
  badge_color: 'blue' | 'emerald' | 'amber' | 'slate' | 'red'
}

export interface HospitalInfo {
  name?: string
  address?: string
  contact?: string
  treating_doctor?: string
  admission_at?: string
  treatment_status: string
  estimated_expenses_inr: number
}

export interface PMRahatInfo {
  scheme_name: string
  cover_limit_inr: number
  confirmed_bills_inr: number
  percent_used: number
  cover_days: number
  day_of_cover: number
  window_ends_at: string
  within_window: boolean
  status_stage: string
  reference_number: string
  eligibility_checklist: Array<{
    title: string
    status: 'verified' | 'pending' | 'expired'
    description: string
  }>
  required_documents: Array<{
    name: string
    required: boolean
    present: boolean
    notes: string
  }>
}

export interface PoliceInfo {
  police_station?: string
  station_name?: string
  station_address?: string
  investigating_officer?: string
  officer_contact?: string
  fir_number?: string
  fir_date?: string
  fir_sections?: string
  stage: string
  draft_status: string
  draft_report: string
  approved_by?: string
  approved_at?: string
}

export interface InsuranceInfo {
  provider?: string
  policy_number?: string
  claim_number?: string
  stage: string
  surveyor_name?: string
  surveyor_phone?: string
  settlement_status?: string
  cashless_garage?: string
}

export interface CaseDocumentItem {
  id: string
  document_name: string
  document_type: string
  category: string
  file_name: string
  file_size: number
  mime_type: string
  document_number?: string
  issuing_authority?: string
  verification_status: string
  resource_type: string
  notes?: string
  download_url: string
  created_at: string
}

export interface FamilyMemberItem {
  user_id: string
  name: string
  role: string
  relationship: string
  contact_number: string
  permissions_summary: string
}

export interface CaseTaskItem {
  task_id: string
  title: string
  description?: string
  priority: 'low' | 'medium' | 'high'
  status: 'open' | 'done'
  due_at?: string
  due_source?: string
  assignee_id?: string
  assignee_name: string
}

export interface TimelineEventItem {
  id: number
  at: string
  actor_id?: string
  actor_name: string
  kind: string
  summary: string
}

export interface WatcherAlertItem {
  id: string
  title: string
  message: string
  severity: string
  source?: {
    title: string
    url: string
  }
  suggested_task?: {
    title: string
    priority: string
  }
}

export interface CaseWorkspaceData {
  case: {
    id: string
    case_number: string
    status: string
    incident_at: string
    accident_time: string
    approximate_location: string
    latitude: number
    longitude: number
    location_landmark?: string
    accident_description?: string
    accident_type: string
    weather_conditions: string
    vehicles_involved: string
    people_affected: string
    victim_display_name?: string
    victim_relationship?: string
    victim_phone?: string
    hospital_name?: string
    injury_severity: string
    injury_description?: string
    damage_severity: string
    damage_description?: string
    vehicle_id?: string
    created_by: string
    created_at: string
    updated_at: string
  }
  vehicle?: {
    id: string
    registration_number: string
    manufacturer: string
    model: string
    variant?: string
    manufacturing_year?: number
    fuel_type?: string
    color?: string
    owner_name?: string
    photo_url?: string
    insurance_provider?: string
    insurance_policy_number?: string
    insurance_expiry?: string
  }
  progress_indicators: {
    hospital: ProgressCard
    police: ProgressCard
    pmrahat: ProgressCard
    insurance: ProgressCard
  }
  hospital_pmrahat: {
    hospital: HospitalInfo
    pmrahat: PMRahatInfo
  }
  police_info: PoliceInfo
  insurance_info: InsuranceInfo
  evidence: {
    all: CaseDocumentItem[]
    accident_photos: CaseDocumentItem[]
    injury_evidence: CaseDocumentItem[]
    supporting_docs: CaseDocumentItem[]
  }
  family_members: FamilyMemberItem[]
  tasks: CaseTaskItem[]
  timeline: TimelineEventItem[]
  alerts: WatcherAlertItem[]
  clock_now: string
  demo_clock_offset_hours: number
}
