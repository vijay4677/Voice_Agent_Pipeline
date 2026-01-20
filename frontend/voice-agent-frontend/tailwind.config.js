/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './app/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            animation: {
                'slide-in': 'slideIn 0.3s ease-out',
                'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'wave': 'wave 1s ease-in-out infinite',
            },
            keyframes: {
                slideIn: {
                    '0%': { transform: 'translateX(100%)', opacity: '0' },
                    '100%': { transform: 'translateX(0)', opacity: '1' },
                },
                wave: {
                    '0%, 100%': { transform: 'scaleY(0.5)' },
                    '50%': { transform: 'scaleY(1)' },
                },
            },
        },
    },
    plugins: [],
}
