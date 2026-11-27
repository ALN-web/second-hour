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
  case_vehicles?: CaseVehicleItem[]
  involved_people?: InvolvedPersonItem[]
  evidence_items?: CaseEvidenceItem[]
  status_transitions?: CaseStatusTransitionItem[]
  reports?: ReportItem[]
  claims?: InsuranceClaimItem[]
  submissions?: ExternalSubmissionItem[]
}

export interface CaseVehicleItem {
  id: string
  case_id: string
  vehicle_id?: string
  registration_number: string
  vehicle_involvement_type: string
  damage_description?: string
  damage_severity: string
  make_model?: string
  color?: string
  driver_name?: string
  driver_contact?: string
  insurance_company?: string
  insurance_policy_no?: string
  is_third_party: boolean
  created_at: string
}

export interface InvolvedPersonItem {
  id: string
  case_id: string
  case_vehicle_id?: string
  associated_user_id?: string
  full_name: string
  involvement_type: string
  relationship_to_coordinator?: string
  contact_number?: string
  reported_injury_status: string
  injury_description?: string
  hospital_name?: string
  treatment_summary?: string
  notes?: string
  created_at: string
}

export interface CaseStatusTransitionItem {
  id: string
  case_id: string
  from_status: string
  to_status: string
  changed_by: string
  transition_trigger: string
  reason?: string
  created_at: string
}

export interface CaseEvidenceItem {
  id: string
  case_id: string
  uploaded_by: string
  evidence_category: string
  title: string
  description?: string
  original_filename: string
  mime_type: string
  file_size_bytes: number
  sha256?: string
  evidence_source: string
  associated_case_vehicle_id?: string
  associated_person_id?: string
  verification_status: string
  capture_timestamp?: string
  geo_latitude?: number
  geo_longitude?: number
  created_at: string
  download_url: string
}

export interface ReportItem {
  id: string
  case_id: string
  title: string
  report_type: string
  report_type_label: string
  status: 'draft' | 'ready_for_review' | 'approved' | 'rejected' | 'archived'
  current_version_id?: string
  current_version_number: number
  generation_source: string
  created_by: string
  approved_by?: string
  approved_at?: string
  archived_at?: string
  created_at: string
  updated_at: string
  download_url: string
  has_file: boolean
  file_size_bytes: number
  sha256?: string
}

export interface ReportVersionItem {
  id: string
  report_id: string
  version_number: number
  content: Record<string, any>
  storage_key?: string
  file_size_bytes: number
  sha256?: string
  generated_by: string
  generation_method: string
  ai_model?: string
  source_references: Array<Record<string, any>>
  version_status: string
  created_at: string
  download_url?: string
}

export interface ReportDetailItem extends ReportItem {
  versions: ReportVersionItem[]
  active_content: Record<string, any>
}

export interface InsuranceClaimItem {
  id: string
  case_id: string
  vehicle_id?: string
  policy_id?: string
  created_by: string
  insurer_name: string
  policy_number: string
  claim_reference_number?: string
  claim_type: string
  incident_date: string
  description: string
  estimated_amount?: number
  approved_amount?: number
  claim_status: string
  filed_at?: string
  settled_at?: string
  surveyor_name?: string
  surveyor_phone?: string
  cashless_garage?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  submissions?: Array<{
    id: string
    external_org_name: string
    submission_method: string
    submission_status: string
    external_reference_number?: string
    submitted_at?: string
    acknowledged_at?: string
  }>
}

export interface ExternalSubmissionItem {
  id: string
  case_id: string
  report_id?: string
  claim_id?: string
  submitted_by: string
  external_org_name: string
  external_org_type: string
  external_reference_number?: string
  submission_method: string
  submission_status: string
  submitted_at?: string
  acknowledged_at?: string
  response_at?: string
  failure_reason?: string
  is_manual: boolean
  is_verified_acknowledgement: boolean
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}
