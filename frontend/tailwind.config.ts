import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Muted green brand palette (sage / moss tones).
        brand: {
          50: '#f4f7f2',
          100: '#e5eddf',
          200: '#c9d9bf',
          300: '#a4bf95',
          400: '#7da26c',
          500: '#5e864e',
          600: '#48693b',
          700: '#3a5431',
          800: '#304429',
          900: '#283823',
          950: '#141e11',
        },
      },
    },
  },
  plugins: [],
};

export default config;
