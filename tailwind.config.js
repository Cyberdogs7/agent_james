const { blackA, gray, red, gold } = require('@radix-ui/colors');

/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['"Roboto"', 'sans-serif'],
            },
            colors: {
                ...gray,
                ...red,
                ...gold,
                ...blackA
            },
            keyframes: {
                shake: {
                  '0%, 100%': { transform: 'translateX(0)' },
                  '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-5px)' },
                  '20%, 40%, 60%, 80%': { transform: 'translateX(5px)' },
                },
            },
            animation: {
                shake: 'shake 0.5s ease-in-out infinite',
            },
        },
    },
    plugins: [],
}
