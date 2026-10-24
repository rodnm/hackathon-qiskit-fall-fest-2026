import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import Landing from './Landing'
import './styles.css'

// / (portada) vs /app (dashboard); Nginx sirve index.html en ambas rutas
const isLanding = window.location.pathname === '/'

createRoot(document.getElementById('root')!).render(
  <StrictMode>{isLanding ? <Landing /> : <App />}</StrictMode>,
)
