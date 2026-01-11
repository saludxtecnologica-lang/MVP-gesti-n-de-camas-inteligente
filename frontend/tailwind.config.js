/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      animation: {
        'borderPulse': 'borderPulse 1.5s ease-in-out infinite',
        'scaleEntrance': 'scaleEntrance 0.3s ease-out',
        'fadeInUp': 'fadeInUp 0.6s ease-out',
        'fadeInUp-delay-1': 'fadeInUp 0.6s ease-out 0.1s both',
        'fadeInUp-delay-2': 'fadeInUp 0.6s ease-out 0.2s both',
        'fadeInUp-delay-3': 'fadeInUp 0.6s ease-out 0.3s both',
      },
      keyframes: {
        borderPulse: {
          '0%, 100%': {
            borderWidth: '2px',
            opacity: '1',
          },
          '50%': {
            borderWidth: '3px',
            opacity: '0.85',
          },
        },
        scaleEntrance: {
          from: {
            opacity: '0',
            transform: 'scale(0.95)',
          },
          to: {
            opacity: '1',
            transform: 'scale(1)',
          },
        },
        fadeInUp: {
          from: {
            opacity: '0',
            transform: 'translateY(20px)',
          },
          to: {
            opacity: '1',
            transform: 'translateY(0)',
          },
        },
      },
    },
  },
  plugins: [],
}