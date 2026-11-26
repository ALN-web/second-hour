
export function HeroIllustration({ className = "w-full max-w-[420px] h-auto" }: { className?: string }) {
  return (
    <div className={`relative flex items-center justify-center select-none ${className}`}>
      {/* Background ambient radial glow */}
      <div className="absolute inset-0 bg-radial from-accent-500/10 via-navy-800/20 to-transparent blur-2xl pointer-events-none rounded-full" />
      
      <svg
        viewBox="0 0 460 360"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto drop-shadow-2xl"
      >
        <defs>
          {/* Gradients */}
          <linearGradient id="shieldGrad" x1="230" y1="20" x2="230" y2="330" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1e3a5f" stopOpacity="0.85" />
            <stop offset="60%" stopColor="#10243f" stopOpacity="0.65" />
            <stop offset="100%" stopColor="#0b1a2e" stopOpacity="0.4" />
          </linearGradient>

          <linearGradient id="shieldBorder" x1="60" y1="20" x2="400" y2="330" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f97316" stopOpacity="0.9" />
            <stop offset="35%" stopColor="#38bdf8" stopOpacity="0.6" />
            <stop offset="70%" stopColor="#f97316" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#1e3a5f" stopOpacity="0.4" />
          </linearGradient>

          <linearGradient id="roadGrad" x1="120" y1="350" x2="340" y2="170" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0b1a2e" stopOpacity="0.95" />
            <stop offset="50%" stopColor="#1e3a5f" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#2a4d7a" stopOpacity="0.4" />
          </linearGradient>

          <linearGradient id="roadBorder" x1="230" y1="350" x2="230" y2="160" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f97316" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.3" />
          </linearGradient>

          <linearGradient id="carGrad" x1="190" y1="200" x2="280" y2="270" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="50%" stopColor="#f1f5f9" />
            <stop offset="100%" stopColor="#cbd5e1" />
          </linearGradient>

          <linearGradient id="glowRing" x1="100" y1="100" x2="360" y2="300" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f97316" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#0284c7" stopOpacity="0.1" />
          </linearGradient>

          <filter id="shieldGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="8" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          <filter id="pulseGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="12" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Ambient Ring */}
        <circle cx="230" cy="180" r="150" stroke="url(#glowRing)" strokeWidth="1.5" strokeDasharray="4 8" className="opacity-60" />
        <circle cx="230" cy="180" r="170" stroke="#38bdf8" strokeOpacity="0.15" strokeWidth="1" strokeDasharray="6 12" />

        {/* Outer Protective Shield Aura */}
        <path
          d="M230 25L95 72C95 180 150 270 230 325C310 270 365 180 365 72L230 25Z"
          fill="url(#shieldGrad)"
          stroke="url(#shieldBorder)"
          strokeWidth="2.5"
          className="transition-all duration-700"
        />

        {/* Inner Shield Contour */}
        <path
          d="M230 42L112 84C112 173 158 250 230 298C302 250 348 173 348 84L230 42Z"
          stroke="#f97316"
          strokeOpacity="0.2"
          strokeWidth="1.5"
          strokeDasharray="5 5"
        />

        {/* Curved Road Way */}
        {/* Left edge of road */}
        <path
          d="M100 350C150 310 180 260 210 210C230 178 245 155 255 140"
          stroke="url(#roadBorder)"
          strokeWidth="2"
          strokeLinecap="round"
        />
        {/* Right edge of road */}
        <path
          d="M330 350C290 310 275 260 265 210C255 178 255 155 255 140"
          stroke="url(#roadBorder)"
          strokeWidth="2"
          strokeLinecap="round"
        />
        {/* Road Surface */}
        <path
          d="M100 350C150 310 180 260 210 210C230 178 245 155 255 140C255 140 255 155 265 210C275 260 290 310 330 350Z"
          fill="url(#roadGrad)"
        />

        {/* Road Center Dashed Line */}
        <path
          d="M208 348C214 310 224 265 237 210C244 182 249 158 255 142"
          stroke="#f8fafc"
          strokeOpacity="0.75"
          strokeWidth="3"
          strokeDasharray="14 10"
          strokeLinecap="round"
        />

        {/* Perspective Road Glow nodes */}
        <circle cx="210" cy="210" r="3" fill="#38bdf8" />
        <circle cx="265" cy="210" r="3" fill="#38bdf8" />
        <circle cx="255" cy="140" r="4" fill="#f97316" filter="url(#shieldGlow)" />

        {/* Vehicle - Sleek Modern Perspective Car */}
        <g transform="translate(195, 222)">
          {/* Vehicle Shadow */}
          <ellipse cx="45" cy="46" rx="36" ry="10" fill="#000000" fillOpacity="0.45" />

          {/* Car Body Main */}
          <path
            d="M16 34C18 29 25 24 35 22L48 18C54 16 62 16 68 20L77 26C83 29 86 33 85 38L83 41C82 43 78 44 72 44H18C13 44 12 40 14 36L16 34Z"
            fill="url(#carGrad)"
            stroke="#1e3a5f"
            strokeWidth="1.5"
          />

          {/* Car Roof & Cabin Glass */}
          <path
            d="M33 22L44 12C47 9 53 8 57 10L68 16C71 18 72 20 72 23L33 22Z"
            fill="#0f172a"
            stroke="#38bdf8"
            strokeWidth="1"
          />
          {/* Windshield Reflection */}
          <path d="M44 14L40 21H55L57 12C54 11 47 11 44 14Z" fill="#38bdf8" fillOpacity="0.4" />

          {/* Headlights & Tail Lights */}
          <circle cx="16" cy="36" r="3" fill="#f97316" filter="url(#shieldGlow)" />
          <path d="M16 36L5 42" stroke="#f97316" strokeOpacity="0.5" strokeWidth="2" strokeLinecap="round" />
          <circle cx="82" cy="33" r="3.5" fill="#38bdf8" filter="url(#shieldGlow)" />
          <path d="M82 33L104 36" stroke="#38bdf8" strokeOpacity="0.4" strokeWidth="3" strokeLinecap="round" />

          {/* Wheels */}
          <g>
            <circle cx="28" cy="42" r="7" fill="#0f172a" stroke="#475569" strokeWidth="2" />
            <circle cx="28" cy="42" r="3" fill="#94a3b8" />
            <circle cx="68" cy="42" r="7" fill="#0f172a" stroke="#475569" strokeWidth="2" />
            <circle cx="68" cy="42" r="3" fill="#94a3b8" />
          </g>
        </g>

        {/* Protective Safety Emblem in Shield Peak */}
        <g transform="translate(214, 52)">
          <circle cx="16" cy="16" r="18" fill="#1e3a5f" stroke="#f97316" strokeWidth="2" />
          <path d="M16 9V17L21 20" stroke="#f8fafc" strokeWidth="2.2" strokeLinecap="round" />
          <circle cx="16" cy="16" r="2" fill="#f97316" />
        </g>

        {/* Ambient Floating Safety Sparkles */}
        <circle cx="140" cy="100" r="3" fill="#38bdf8" fillOpacity="0.8" />
        <circle cx="320" cy="115" r="2.5" fill="#f97316" fillOpacity="0.9" />
        <circle cx="120" cy="220" r="2" fill="#ffffff" fillOpacity="0.7" />
        <circle cx="340" cy="240" r="3" fill="#38bdf8" fillOpacity="0.7" />
      </svg>
    </div>
  )
}
