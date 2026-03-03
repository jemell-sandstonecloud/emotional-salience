/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sand: { 50:'#fdf8f0', 100:'#f7eddb', 200:'#eddab5', 300:'#e0c182', 400:'#d4a959', 500:'#c4903a', 600:'#a4722f', 700:'#845a28', 800:'#6d4a26', 900:'#5c3f24' },
      },
    },
  },
  plugins: [],
};
