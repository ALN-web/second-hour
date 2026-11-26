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
  onOpenProfile: () => void
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
  onOpenProfile,
  onOpenVehicles,
  activeCaseNumber,
}: NavbarProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
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
    { id: 'profile', label: 'My Profile', action: onOpenProfile },
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

  return (
    <header className="sticky top-0 z-40 bg-navy-950 border-b border-navy-900 shadow-md">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          
          {/* Left: Brand Logo & Title */}
          <div 
            onClick={() => onNavigate('home')} 
            className="flex items-center gap-3 cursor-pointer group select-none"
          >
            <div className="transition-transform group-hover:scale-105">
              <ShieldLogo className="h-8 w-8" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-bold tracking-tight text-white leading-tight">
                Second <span className="text-accent-500">Hour</span>
              </span>
              <span className="text-[10px] text-slate-400 font-medium tracking-wider uppercase -mt-0.5 hidden sm:block">
                Accident Support & PM-RAHAT
              </span>
            </div>
            {activeCaseNumber && (
              <span className="ml-2 hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-navy-800 text-slate-200 border border-slate-700">
                {activeCaseNumber}
              </span>
            )}
          </div>

          {/* Center: Desktop Navigation Bar */}
          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = activeNav === link.id
              return (
                <button
                  key={link.id}
                  onClick={() => handleNavClick(link)}
                  className={`relative px-3.5 py-2 text-sm font-medium rounded-lg transition-all ${
                    isActive
                      ? 'text-white bg-white/10'
                      : 'text-slate-300 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <span>{link.label}</span>
                  {isActive && (
                    <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-accent-500 rounded-full" />
                  )}
                </button>
              )
            })}
          </nav>

          {/* Right: Actions, Notifications & Profile Avatar */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Notification Bell */}
            <button
              onClick={onOpenNotifications}
              className="relative p-2 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 transition"
              title="Notifications"
            >
              <BellIcon className="h-5 w-5" />
              {/* Notification Badge Dot */}
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-accent-500 ring-2 ring-navy-950" />
            </button>

            {/* User Profile Avatar with Dropdown */}
            {user ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2 p-1.5 pl-2 rounded-xl hover:bg-white/10 text-left transition border border-transparent hover:border-slate-700"
                >
                  <div className="h-8 w-8 rounded-full bg-navy-800 border border-accent-500 text-white font-bold text-xs flex items-center justify-center">
                    {user.name ? user.name[0] : 'U'}
                  </div>
                  <div className="hidden sm:block text-left pr-1">
                    <div className="text-xs font-semibold text-white leading-tight truncate max-w-[100px]">
                      {user.name}
                    </div>
                    <div className="text-[10px] text-slate-400 leading-none">
                      {user.role_label}
                    </div>
                  </div>
                  <ChevronDownIcon className="h-3.5 w-3.5 text-slate-400" />
                </button>

                {/* Dropdown Menu */}
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-white border border-slate-200 shadow-2xl py-2 z-50 text-slate-800 animate-fade-in">
                    <div className="px-4 py-2 border-b border-slate-100">
                      <div className="text-xs font-bold text-navy-900">{user.name}</div>
                      <div className="text-[11px] text-slate-500">{user.role_label}</div>
                      <span className="inline-block mt-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                        Verified Coordinator
                      </span>
                    </div>

                    <button
                      onClick={() => { onOpenProfile(); setDropdownOpen(false) }}
                      className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 font-medium text-slate-700 flex items-center gap-2"
                    >
                      <span>👤</span> My Profile Details
                    </button>
                    <button
                      onClick={() => { onOpenVehicles(); setDropdownOpen(false) }}
                      className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 font-medium text-slate-700 flex items-center gap-2"
                    >
                      <span>🚗</span> Registered Vehicles
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
            ) : (
              <button
                onClick={onSwitchUser}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition"
              >
                Sign In
              </button>
            )}

            {/* Mobile Menu Hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 transition"
              aria-label="Toggle mobile navigation menu"
            >
              {mobileMenuOpen ? <CloseIcon className="h-6 w-6" /> : <MenuIcon className="h-6 w-6" />}
            </button>
          </div>

        </div>

        {/* Mobile Dropdown Navigation */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-3 border-t border-navy-900 space-y-1">
            {navLinks.map((link) => {
              const isActive = activeNav === link.id
              return (
                <button
                  key={link.id}
                  onClick={() => handleNavClick(link)}
                  className={`w-full text-left px-4 py-2.5 rounded-xl text-sm font-medium flex items-center justify-between ${
                    isActive
                      ? 'bg-accent-500/15 text-accent-400 font-semibold border-l-4 border-accent-500'
                      : 'text-slate-300 hover:bg-white/5 hover:text-white'
                  }`}
                >
                  <span>{link.label}</span>
                  {isActive && <span className="text-accent-500">●</span>}
                </button>
              )
            })}
          </div>
        )}

      </div>
    </header>
  )
}
