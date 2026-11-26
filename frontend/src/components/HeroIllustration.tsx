export function HeroIllustration({ className = "w-full max-w-[460px] h-auto" }: { className?: string }) {
  return (
    <div className={`relative flex items-center justify-center select-none ${className}`}>
      {/* Background ambient radial blue glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[340px] h-[340px] bg-blue-600/20 rounded-full blur-3xl pointer-events-none" />
      
      <svg
        viewBox="0 0 520 380"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-auto drop-shadow-2xl overflow-visible"
      >
        <defs>
          {/* Radial back glow */}
          <radialGradient id="centerBlueGlow" cx="50%" cy="45%" r="45%">
            <stop offset="0%" stopColor="#1d4ed8" stopOpacity="0.45" />
            <stop offset="60%" stopColor="#0f2b5c" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#0a192f" stopOpacity="0" />
          </radialGradient>

          {/* Shield Fill Gradient */}
          <linearGradient id="refShieldFill" x1="280" y1="60" x2="280" y2="240" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1e3a68" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0d2142" stopOpacity="0.95" />
          </linearGradient>

          {/* Shield Border Gradient */}
          <linearGradient id="refShieldBorder" x1="220" y1="60" x2="340" y2="240" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#60a5fa" />
            <stop offset="50%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#1d4ed8" />
          </linearGradient>

          {/* Road Surface Gradient */}
          <linearGradient id="refRoadSurface" x1="100" y1="360" x2="480" y2="200" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#0c1f38" stopOpacity="0.95" />
            <stop offset="60%" stopColor="#122c54" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#0a192f" stopOpacity="0.4" />
          </linearGradient>

          {/* Orange Right Shoulder Glow */}
          <linearGradient id="refOrangeCurve" x1="200" y1="360" x2="480" y2="200" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#ff7a18" stopOpacity="1" />
            <stop offset="60%" stopColor="#ea580c" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#ff8a2b" stopOpacity="0.2" />
          </linearGradient>

          {/* Glow filter */}
          <filter id="roadOrangeGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>

          <filter id="shieldCyanGlow" x="-25%" y="-25%" width="150%" height="150%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Ambient Back Glow Circle */}
        <circle cx="290" cy="160" r="140" fill="url(#centerBlueGlow)" />

        {/* =================================================== CURVED HIGHWAY */}
        {/* Road Surface */}
        <path
          d="M 120 370 C 230 330, 310 270, 370 210 C 410 170, 440 145, 470 135 L 490 145 C 460 160, 420 190, 370 240 C 300 310, 220 365, 120 370 Z"
          fill="url(#refRoadSurface)"
        />

        {/* Left Road Shoulder Line (Soft White/Cyan) */}
        <path
          d="M 120 370 C 230 330, 310 270, 370 210 C 410 170, 440 145, 470 135"
          stroke="#93c5fd"
          strokeWidth="2.5"
          strokeOpacity="0.75"
          strokeLinecap="round"
        />

        {/* Road Center Dashed Line */}
        <path
          d="M 150 370 C 240 335, 315 285, 365 235 C 400 200, 430 170, 460 150"
          stroke="#ffffff"
          strokeWidth="3.5"
          strokeDasharray="16 12"
          strokeLinecap="round"
          strokeOpacity="0.85"
        />

        {/* Right Road Shoulder Line (VIBRANT GLOWING ORANGE) */}
        <path
          d="M 210 380 C 290 345, 360 295, 410 240 C 445 200, 470 170, 490 155"
          stroke="url(#refOrangeCurve)"
          strokeWidth="4.5"
          strokeLinecap="round"
          filter="url(#roadOrangeGlow)"
        />
        {/* Secondary brighter core orange line */}
        <path
          d="M 210 380 C 290 345, 360 295, 410 240 C 445 200, 470 170, 490 155"
          stroke="#ffedd5"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeOpacity="0.8"
        />

        {/* =================================================== PROTECTIVE SHIELD */}
        <g transform="translate(210, 50)">
          {/* Shield Outer Glow Outline */}
          <path
            d="M 80 10 L 20 40 C 20 115, 45 160, 80 185 C 115 160, 140 115, 140 40 L 80 10 Z"
            fill="url(#refShieldFill)"
            stroke="url(#refShieldBorder)"
            strokeWidth="3.5"
            strokeLinejoin="round"
            filter="url(#shieldCyanGlow)"
          />

          {/* Shield Crisp Border */}
          <path
            d="M 80 10 L 20 40 C 20 115, 45 160, 80 185 C 115 160, 140 115, 140 40 L 80 10 Z"
            fill="none"
            stroke="#93c5fd"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeOpacity="0.9"
          />

          {/* FRONT-FACING CAR SILHOUETTE INSIDE SHIELD */}
          <g transform="translate(48, 70)">
            {/* Car Cabin & Windshield */}
            <path
              d="M 16 18 L 20 4 C 21 1.5, 23 0, 26 0 L 38 0 C 41 0, 43 1.5, 44 4 L 48 18 Z"
              fill="#bfdbfe"
              fillOpacity="0.9"
            />
            {/* Windshield Glass Inset */}
            <path
              d="M 19 16 L 22 5 C 22.5 3.5, 24 2.5, 26 2.5 L 38 2.5 C 40 2.5, 41.5 3.5, 42 5 L 45 16 Z"
              fill="#1e3a68"
            />

            {/* Car Lower Body */}
            <rect
              x="8"
              y="16"
              width="48"
              height="20"
              rx="6"
              fill="#bfdbfe"
              fillOpacity="0.95"
            />

            {/* Front Headlights */}
            <rect x="12" y="21" width="8" height="5" rx="2" fill="#1e3a68" />
            <circle cx="16" cy="23.5" r="1.5" fill="#ffffff" />

            <rect x="44" y="21" width="8" height="5" rx="2" fill="#1e3a68" />
            <circle cx="48" cy="23.5" r="1.5" fill="#ffffff" />

            {/* Front Grille */}
            <rect x="24" y="25" width="16" height="4" rx="1.5" fill="#1e3a68" />

            {/* Wheels / Tires Bottom */}
            <rect x="11" y="34" width="7" height="6" rx="2" fill="#0f2347" />
            <rect x="46" y="34" width="7" height="6" rx="2" fill="#0f2347" />
          </g>
        </g>
      </svg>
    </div>
  )
}
