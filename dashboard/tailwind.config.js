/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#F2F7F4',
          100: '#E1EDE6',
          200: '#C2DBCB',
          300: '#94C1A5',
          400: '#5F9F78',
          500: '#2D5A3D', // Primary Brand Green
          600: '#234931',
          700: '#1C3B27',
          800: '#162E1F',
          900: '#0F2015',
        },
        amber: {
          50: '#FDF8F0',
          100: '#F9ECCF',
          200: '#F3D89E',
          300: '#EABF66',
          400: '#E3A83F',
          500: '#D98E32', // Secondary Amber
          600: '#BA7224',
          700: '#94541C',
          800: '#78431C',
          900: '#64371A',
        },
      },
    },
  },
  plugins: [],
}

