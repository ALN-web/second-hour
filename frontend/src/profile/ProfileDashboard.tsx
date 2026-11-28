import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import type {
  AddressItem,
  EmergencyContactItem,
  IdentityDocItem,
  MedicalInfoData,
  NotificationPreferences,
  PrivacyPreferences,
  SecurityOverview,
  UserProfileData,
} from './types'
import { ProfileHeader } from './ProfileHeader'
import { ProfileSummaryCards } from './ProfileSummaryCards'
import { PersonalInfoSection } from './PersonalInfoSection'
import { EmergencyContactsSection } from './EmergencyContactsSection'
import { MedicalInfoSection } from './MedicalInfoSection'
import { AddressSection } from './AddressSection'
import { IdentityDocumentsSection } from './IdentityDocumentsSection'
import { AccountSecuritySection } from './AccountSecuritySection'
import { PrivacyPermissionsSection } from './PrivacyPermissionsSection'
import { NotificationPreferencesSection } from './NotificationPreferencesSection'
import { OtpVerificationModal } from './OtpVerificationModal'

export type ProfileTab =
  | 'personal'
  | 'contacts'
  | 'medical'
  | 'address'
  | 'identity'
  | 'security'
  | 'privacy'
  | 'notifications'

interface ProfileDashboardProps {
  user: { user_id: string; name: string; role_label: string } | null
  onBackHome: () => void
  onNavigateToVehicles: () => void
  onNavigateToDocuments: () => void
  onNavigateToCases: () => void
}

export function ProfileDashboard({
  user,
  onBackHome,
  onNavigateToVehicles,
  onNavigateToDocuments,
}: ProfileDashboardProps) {
  const [activeTab, setActiveTab] = useState<ProfileTab>('personal')
  const [loading, setLoading] = useState(true)

  // Data states
  const [profile, setProfile] = useState<UserProfileData | null>(null)
  const [contacts, setContacts] = useState<EmergencyContactItem[]>([])
  const [medical, setMedical] = useState<MedicalInfoData | null>(null)
  const [addresses, setAddresses] = useState<{ current: AddressItem | null; permanent: AddressItem | null }>({
    current: null,
    permanent: null,
  })
  const [identityDocs, setIdentityDocs] = useState<IdentityDocItem[]>([])
  const [privacy, setPrivacy] = useState<PrivacyPreferences | null>(null)
  const [notifications, setNotifications] = useState<NotificationPreferences | null>(null)
  const [security, setSecurity] = useState<SecurityOverview | null>(null)

  // Verification modal state
  const [verifyModalChannel, setVerifyModalChannel] = useState<'email' | 'phone' | null>(null)

  const loadAllData = useCallback(async () => {
    try {
      setLoading(true)
      const [
        pData,
        cData,
        mData,
        aData,
        idData,
        privData,
        notifData,
        secData,
      ] = await Promise.all([
        api<UserProfileData>('/api/profile'),
        api<EmergencyContactItem[]>('/api/profile/contacts'),
        api<MedicalInfoData>('/api/profile/medical'),
        api<{ current: AddressItem | null; permanent: AddressItem | null }>('/api/profile/addresses'),
        api<IdentityDocItem[]>('/api/profile/identity-documents'),
        api<PrivacyPreferences>('/api/profile/privacy'),
        api<NotificationPreferences>('/api/profile/notifications'),
        api<SecurityOverview>('/api/profile/security'),
      ])

      setProfile(pData)
      setContacts(cData)
      setMedical(mData)
      setAddresses(aData)
      setIdentityDocs(idData)
      setPrivacy(privData)
      setNotifications(notifData)
      setSecurity(secData)
    } catch (err) {
      console.error('Failed to load profile data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAllData()
  }, [loadAllData, user?.user_id])

  // Handlers
  const handleSavePersonalInfo = async (data: Partial<UserProfileData>) => {
    const updated = await api<UserProfileData>('/api/profile', {
      method: 'PATCH',
      body: data,
    })
    setProfile(updated)
  }

  const handleAddContact = async (data: any) => {
    await api('/api/profile/contacts', {
      method: 'POST',
      body: data,
    })
    const cData = await api<EmergencyContactItem[]>('/api/profile/contacts')
    setContacts(cData)
    const pData = await api<UserProfileData>('/api/profile')
    setProfile(pData)
  }

  const handleUpdateContact = async (contactId: string, data: any) => {
    await api(`/api/profile/contacts/${contactId}`, {
      method: 'PATCH',
      body: data,
    })
    const cData = await api<EmergencyContactItem[]>('/api/profile/contacts')
    setContacts(cData)
  }

  const handleDeleteContact = async (contactId: string) => {
    await api(`/api/profile/contacts/${contactId}`, { method: 'DELETE' })
    const cData = await api<EmergencyContactItem[]>('/api/profile/contacts')
    setContacts(cData)
    const pData = await api<UserProfileData>('/api/profile')
    setProfile(pData)
  }

  const handleSetPrimaryContact = async (contactId: string) => {
    await api(`/api/profile/contacts/${contactId}/primary`, { method: 'POST' })
    const cData = await api<EmergencyContactItem[]>('/api/profile/contacts')
    setContacts(cData)
  }

  const handleReorderContacts = async (ids: string[]) => {
    const cData = await api<EmergencyContactItem[]>('/api/profile/contacts/reorder', {
      method: 'POST',
      body: { ordered_ids: ids },
    })
    setContacts(cData)
  }

  const handleSaveMedical = async (data: Partial<MedicalInfoData>) => {
    const mData = await api<MedicalInfoData>('/api/profile/medical', {
      method: 'PATCH',
      body: data,
    })
    setMedical(mData)
  }

  const handleClearMedical = async () => {
    const mData = await api<MedicalInfoData>('/api/profile/medical', { method: 'DELETE' })
    setMedical(mData)
  }

  const handleSaveAddress = async (type: 'current' | 'permanent', data: any) => {
    const aData = await api<{ current: AddressItem | null; permanent: AddressItem | null }>(
      `/api/profile/addresses/${type}`,
      { method: 'POST', body: data }
    )
    setAddresses(aData)
    const pData = await api<UserProfileData>('/api/profile')
    setProfile(pData)
  }

  const handleSavePrivacy = async (data: Partial<PrivacyPreferences>) => {
    const privData = await api<PrivacyPreferences>('/api/profile/privacy', {
      method: 'PATCH',
      body: data,
    })
    setPrivacy(privData)
  }

  const handleSaveNotifications = async (data: Partial<NotificationPreferences>) => {
    const notifData = await api<NotificationPreferences>('/api/profile/notifications', {
      method: 'PATCH',
      body: data,
    })
    setNotifications(notifData)
  }

  const handleChangePassword = async (current_password: string, new_password: string) => {
    await api('/api/profile/security/change-password', {
      method: 'POST',
      body: { current_password, new_password },
    })
  }

  const handleDeleteAccount = async (confirmation: string) => {
    return api<{ status: string; message: string }>('/api/profile/security/delete-account', {
      method: 'POST',
      body: { confirmation },
    })
  }

  if (loading || !profile) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-9 h-9 mx-auto border-3 border-[#ff7518] border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-500 font-medium">Loading personal profile & emergency settings...</p>
        </div>
      </div>
    )
  }

  const tabs: { id: ProfileTab; label: string; count?: number; badge?: string }[] = [
    { id: 'personal', label: 'Personal Information' },
    { id: 'contacts', label: 'Emergency Contacts', count: contacts.length },
    { id: 'medical', label: 'Medical Info (Optional)' },
    { id: 'address', label: 'Address Records' },
    { id: 'identity', label: 'Identity Documents', count: identityDocs.length },
    { id: 'security', label: 'Account & Security' },
    { id: 'privacy', label: 'Privacy & AI' },
    { id: 'notifications', label: 'Notifications' },
  ]

  return (
    <div className="min-h-screen bg-slate-50 pb-16">
      {/* 1. Profile Header */}
      <ProfileHeader
        profile={profile}
        onBackHome={onBackHome}
        onOpenVerifyModal={(ch) => setVerifyModalChannel(ch)}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* 2. Profile Summary Metrics */}
        <ProfileSummaryCards
          profile={profile}
          onNavigateToVehicles={onNavigateToVehicles}
          onSelectTab={(tId) => setActiveTab(tId as ProfileTab)}
        />

        {/* 3. Navigation Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-3 mb-6 scrollbar-none border-b border-slate-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`shrink-0 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-[#091528] text-white shadow-md shadow-[#091528]/20'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                    activeTab === tab.id
                      ? 'bg-white/20 text-white'
                      : 'bg-slate-200 text-slate-700'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* 4. Active Section Content */}
        <div className="transition-all duration-150">
          {activeTab === 'personal' && (
            <PersonalInfoSection
              profile={profile}
              onSave={handleSavePersonalInfo}
              onOpenVerifyModal={(ch) => setVerifyModalChannel(ch)}
            />
          )}

          {activeTab === 'contacts' && (
            <EmergencyContactsSection
              contacts={contacts}
              onAddContact={handleAddContact}
              onUpdateContact={handleUpdateContact}
              onDeleteContact={handleDeleteContact}
              onSetPrimary={handleSetPrimaryContact}
              onReorder={handleReorderContacts}
            />
          )}

          {activeTab === 'medical' && medical && (
            <MedicalInfoSection
              medicalInfo={medical}
              onSave={handleSaveMedical}
              onClear={handleClearMedical}
            />
          )}

          {activeTab === 'address' && (
            <AddressSection
              addresses={addresses}
              onSaveAddress={handleSaveAddress}
            />
          )}

          {activeTab === 'identity' && (
            <IdentityDocumentsSection
              documents={identityDocs}
              onNavigateToDocuments={onNavigateToDocuments}
              onRefresh={loadAllData}
            />
          )}

          {activeTab === 'security' && security && (
            <AccountSecuritySection
              security={security}
              onChangePassword={handleChangePassword}
              onDeleteAccount={handleDeleteAccount}
            />
          )}

          {activeTab === 'privacy' && privacy && (
            <PrivacyPermissionsSection
              preferences={privacy}
              onSave={handleSavePrivacy}
            />
          )}

          {activeTab === 'notifications' && notifications && (
            <NotificationPreferencesSection
              preferences={notifications}
              onSave={handleSaveNotifications}
            />
          )}
        </div>
      </div>

      {/* OTP Verification Modal */}
      <OtpVerificationModal
        isOpen={Boolean(verifyModalChannel)}
        channel={verifyModalChannel}
        target={
          verifyModalChannel === 'email'
            ? profile.email || ''
            : profile.phone || ''
        }
        onClose={() => setVerifyModalChannel(null)}
        onSuccess={loadAllData}
      />
    </div>
  )
}
