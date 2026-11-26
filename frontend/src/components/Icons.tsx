// Exact SVG Icons matching the reference design

// 1. Second Hour Shield + Clock Logo
export function ShieldLogo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Outer Shield Outline */}
      <path
        d="M18 3L6 8V17C6 24.5 11.2 31.2 18 33C24.8 31.2 30 24.5 30 17V8L18 3Z"
        fill="#0d1f38"
        stroke="#ffffff"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {/* Inner Orange Clock Accent */}
      <circle cx="18" cy="18" r="7.5" stroke="#f97316" strokeWidth="2" />
      {/* Clock Hands pointing to 10:10 / second hour */}
      <path d="M18 13.5V18L21.5 19.5" stroke="#f97316" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

// 2. Emergency Siren Icon (pill CTA)
export function SirenIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2v3" />
      <path d="M4.93 4.93l2.12 2.12" />
      <path d="M19.07 4.93l-2.12 2.12" />
      <path d="M5 19h14" />
      <path d="M6 19a6 6 0 0 1 12 0" />
      <line x1="2" y1="13" x2="5" y2="13" />
      <line x1="19" y1="13" x2="22" y2="13" />
    </svg>
  )
}

// 3. Arrow Right
export function ArrowRightIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  )
}

// 4. Info Icon (pill Learn More)
export function InfoIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <circle cx="12" cy="8" r="1" fill="currentColor" />
    </svg>
  )
}

// 5. Front-Facing Car Icon (Blue Card)
export function FrontCarIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 11l1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11" />
      <rect x="3" y="11" width="18" height="7" rx="2" />
      <circle cx="7" cy="14.5" r="1.25" fill="currentColor" />
      <circle cx="17" cy="14.5" r="1.25" fill="currentColor" />
      <path d="M5 18v2" />
      <path d="M19 18v2" />
      <line x1="10" y1="15" x2="14" y2="15" />
    </svg>
  )
}

// 6. Orange Document Icon (Orange Card)
export function DocumentCardIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="14" y2="17" />
    </svg>
  )
}

// 7. Green Shield Check Icon (Green Card)
export function ShieldCheckCardIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  )
}

// 8. Robot AI Assistant Icon (Purple Card)
export function RobotAssistantIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="9" width="16" height="12" rx="3" />
      <circle cx="9" cy="14" r="1.5" fill="currentColor" />
      <circle cx="15" cy="14" r="1.5" fill="currentColor" />
      <path d="M12 2v4" />
      <circle cx="12" cy="2" r="1" fill="currentColor" />
      <path d="M9 18h6" />
      <path d="M2 13v4" />
      <path d="M22 13v4" />
    </svg>
  )
}

// 9. Solid Green Checkmark in Circle
export function SolidGreenCheck({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10" cy="10" r="9" fill="#10b981" />
      <path d="M6.5 10.2L8.8 12.5L13.5 7.8" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// 10. Calendar Icon for Reminder
export function CalendarReminderIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
      <path d="M8 14h.01" strokeWidth="2.5" />
      <path d="M12 14h.01" strokeWidth="2.5" />
      <path d="M16 14h.01" strokeWidth="2.5" />
      <path d="M8 18h.01" strokeWidth="2.5" />
      <path d="M12 18h.01" strokeWidth="2.5" />
    </svg>
  )
}

// 11. Heartbeat / Pulse Icon (Emergency call 112)
export function PulseHeartIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="12" fill="#ff7a18" />
      <path
        d="M6 12h2.5l1.5-3.5 2.5 7 2-4.5 1.5 2H18"
        stroke="#ffffff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// 12. National Emblem of India / Ashoka Stambh Lion Capital Icon
export function AshokaEmblemIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      {/* Stylized State Emblem silhouette */}
      <path d="M12 2C10.5 2 9.5 3 9.5 4.5c0 .6.2 1.1.6 1.5-.6.3-1.1.8-1.4 1.5-.5-.3-1.1-.4-1.7-.2-.8.3-1.3 1-1.3 1.8 0 .4.1.8.4 1.1-.7.5-1.1 1.3-1.1 2.2 0 1.2.7 2.2 1.7 2.6v.5h14v-.5c1-.4 1.7-1.4 1.7-2.6 0-.9-.4-1.7-1.1-2.2.3-.3.4-.7.4-1.1 0-.8-.5-1.5-1.3-1.8-.6-.2-1.2-.1-1.7.2-.3-.7-.8-1.2-1.4-1.5.4-.4.6-.9.6-1.5C14.5 3 13.5 2 12 2zm-5 14v1.5h10V16H7zm-1 2.5v1.5h12v-1.5H6zM4 21v1h16v-1H4z" />
    </svg>
  )
}

// 13. Solid Green Shield Icon (Insurance & claims)
export function SolidGreenShieldIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2L4 5.5v6.5c0 5.5 3.5 10.5 8 12 4.5-1.5 8-6.5 8-12V5.5L12 2z"
        fill="#10b981"
      />
      <path
        d="m8.5 11.5 2.5 2.5 4.5-4.5"
        stroke="#ffffff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// 14. Handshake Icon (Support for your family)
export function HandshakeIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="m11 17 2 2a1 1 0 0 0 1.4 0l4.6-4.6a2 2 0 0 0 0-2.8l-3.5-3.5a2 2 0 0 0-2.8 0L9 11.8" />
      <path d="m3 14 3.5-3.5a2 2 0 0 1 2.8 0l3.5 3.5a2 2 0 0 1 0 2.8L8.2 21.4a1 1 0 0 1-1.4 0L4 18.6a2 2 0 0 1 0-2.8l1.4-1.4" />
      <path d="m18 10 3-3a2 2 0 0 0 0-2.8l-1.4-1.4a2 2 0 0 0-2.8 0l-3 3" />
      <path d="m6 6-3 3a2 2 0 0 0 0 2.8l1.4 1.4" />
    </svg>
  )
}

// 15. Bell Icon
export function BellIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  )
}

// 16. Chevron Down
export function ChevronDownIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  )
}

// 17. Chevron Right
export function ChevronRightIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

// 18. Mobile Menu Icon
export function MenuIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="20" y2="18" />
    </svg>
  )
}

// 19. Close Icon
export function CloseIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

// 20. User Icon
export function UserIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

// Aliases
export { FrontCarIcon as CarIcon, SolidGreenCheck as CheckCircleIcon }
