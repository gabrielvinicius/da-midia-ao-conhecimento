// tailwind.config.js
module.exports = {
    darkMode: "class",
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
            colors: {
                primary: '#3B82F6',
                secondary: '#6B7280',
            },
        },
    },
    plugins: [require('@tailwindcss/forms')],
}