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
            }
        },
    },
    plugins: [],
}
