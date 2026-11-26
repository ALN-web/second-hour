import { useState, useRef, useEffect } from 'react'
import { ShieldLogo, BellIcon, ChevronDownIcon, MenuIcon, CloseIcon } from './Icons'

export type NavItem = 'home' | 'profile' | 'vehicles' | 'cases' | 'documents' | 'ai-assistant'

interface NavbarProps {
  activeNav: NavItem
  onNavigate: (nav: NavItem) => void
  user: { user_id: string; name: string; role_label: string } | null
  onSwitchUser: () => void
  onLogout: () => void
  onOpenNotifications: () => void
  onOpenProfile?: () => void
  onOpenVehicles: () => void
  activeCaseNumber?: string | null
}

export function Navbar({
  activeNav,
  onNavigate,
  user,
  onSwitchUser,
  onLogout,
  onOpenNotifications,
  onOpenVehicles,
  activeCaseNumber,
}: NavbarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const navLinks: { id: NavItem; label: string; action?: () => void }[] = [
    { id: 'home', label: 'Home' },
    { id: 'profile', label: 'My Profile' },
    { id: 'vehicles', label: 'My Vehicles', action: onOpenVehicles },
    { id: 'cases', label: 'My Cases' },
    { id: 'documents', label: 'Documents' },
    { id: 'ai-assistant', label: 'AI Assistant' },
  ]

  const handleNavClick = (link: typeof navLinks[number]) => {
    if (link.action) {
      link.action()
    } else {
      onNavigate(link.id)
    }
    setMobileMenuOpen(false)
  }

  // Display initials like "RS" or user initials
  const initials = user?.name
    ? user.name
        .split(' ')
        .map((p) => p[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : 'RS'

  return (
    <header className="sticky top-0 z-40 bg-[#091528] border-b border-[#13243d]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          
          {/* Left: Brand Logo & Title */}
          <div 
            onClick={() => onNavigate('home')} 
            className="flex items-center gap-2.5 cursor-pointer select-none group"
          >
            <ShieldLogo className="h-8 w-8" />
            <span className="text-xl font-bold tracking-tight text-white">
              Second <span className="text-[#ff7a18]">Hour</span>
            </span>
            {activeCaseNumber && (
              <span className="ml-2 hidden xl:inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#1a2d48] text-slate-300">
                {activeCaseNumber}
              </span>
            )}
          </div>

          {/* Center: Desktop Navigation Bar */}
          <nav className="hidden lg:flex items-center gap-3">
            {navLinks.map((link) => {
              const isActive = activeNav === link.id
              return (
                <div key={link.id} className="relative flex flex-col items-center">
                  <button
                    onClick={() => handleNavClick(link)}
                    className={`px-4 py-1.5 text-xs font-semibold rounded-full transition-all ${
                      isActive
                        ? 'text-white bg-[#1a2e4c]'
                        : 'text-slate-300 hover:text-white'
                    }`}
                  >
                    {link.label}
                  </button>
                  {/* Subtle orange indicator bar centered under active link */}
                  {isActive && (
                    <span className="w-6 h-1 bg-[#ff7a18] rounded-full mt-1 -mb-2" />
                  )}
                </div>
              )
            })}
          </nav>

          {/* Right: Notifications & User Avatar */}
          <div className="flex items-center gap-3">
            {/* Notification Bell with Red Badge */}
            <button
              onClick={onOpenNotifications}
              className="relative p-2 text-slate-300 hover:text-white transition"
              title="Notifications"
            >
              <BellIcon className="h-5 w-5" />
              {/* Red dot badge with number */}
              <span className="absolute top-1.5 right-1.5 h-3.5 w-3.5 rounded-full bg-[#ef4444] text-white text-[9px] font-bold flex items-center justify-center">
                1
              </span>
            </button>

            {/* Avatar Circle with Chevron */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-1.5 p-1 rounded-full hover:bg-white/10 transition"
              >
                <div className="h-8 w-8 rounded-full bg-[#1b2f4d] border border-[#2b4d7e] text-white font-bold text-xs flex items-center justify-center">
                  {initials}
                </div>
                <ChevronDownIcon className="h-3.5 w-3.5 text-slate-300" />
              </button>

              {/* Dropdown Menu */}
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-white border border-slate-200 shadow-2xl py-2 z-50 text-slate-800">
                  <div className="px-4 py-2 border-b border-slate-100">
                    <div className="text-xs font-bold text-navy-950">{user?.name || 'Ravi Sharma'}</div>
                    <div className="text-[11px] text-slate-500">{user?.role_label || 'Family Member'}</div>
                  </div>

                  <button
                    onClick={() => { onNavigate('profile'); setDropdownOpen(false) }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 font-medium text-slate-700 flex items-center gap-2"
                  >
                    <span>👤</span> My Profile
                  </button>
                  <button
                    onClick={() => { onOpenVehicles(); setDropdownOpen(false) }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 font-medium text-slate-700 flex items-center gap-2"
                  >
                    <span>🚗</span> My Vehicles
                  </button>
                  <button
                    onClick={() => { onSwitchUser(); setDropdownOpen(false) }}
                    className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 font-medium text-navy-800 flex items-center gap-2"
                  >
                    <span>🔄</span> Switch Family Member
                  </button>

                  <div className="pt-1 mt-1 border-t border-slate-100">
                    <button
                      onClick={() => { onLogout(); setDropdownOpen(false) }}
                      className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 font-medium flex items-center gap-2"
                    >
                      <span>🚪</span> Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Mobile Hamburger Toggle */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 text-slate-300 hover:text-white"
            >
              {mobileMenuOpen ? <CloseIcon className="h-6 w-6" /> : <MenuIcon className="h-6 w-6" />}
            </button>
          </div>

        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-3 border-t border-[#13243d] space-y-1">
            {navLinks.map((link) => {
              const isActive = activeNav === link.id
              return (
                <button
                  key={link.id}
                  onClick={() => handleNavClick(link)}
                  className={`w-full text-left px-4 py-2.5 rounded-xl text-sm font-medium flex items-center justify-between ${
                    isActive
                      ? 'bg-[#1a2e4c] text-white font-semibold'
                      : 'text-slate-300 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <span>{link.label}</span>
                  {isActive && <span className="text-[#ff7a18]">●</span>}
                </button>
              )
            })}
          </div>
        )}

      </div>
    </header>
  )
}
