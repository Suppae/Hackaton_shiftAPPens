import { useState } from 'react'
import useStore from '@/store'

export default function LayersToggle() {
  const [isOpen, setIsOpen] = useState(true)
  
  const showCompass = useStore((s) => s.showCompass)
  const showWindHUD = useStore((s) => s.showWindHUD)
  const showTimeSlider = useStore((s) => s.showTimeSlider)
  const showRoutePanel = useStore((s) => s.showRoutePanel)
  const showLegend = useStore((s) => s.showLegend)

  const setShowCompass = useStore((s) => s.setShowCompass)
  const setShowWindHUD = useStore((s) => s.setShowWindHUD)
  const setShowTimeSlider = useStore((s) => s.setShowTimeSlider)
  const setShowRoutePanel = useStore((s) => s.setShowRoutePanel)
  const setShowLegend = useStore((s) => s.setShowLegend)

  const toggles = [
    { label: 'Bussola', value: showCompass, onChange: setShowCompass },
    { label: 'Vento', value: showWindHUD, onChange: setShowWindHUD },
    { label: 'Wildfire Routing', value: showRoutePanel, onChange: setShowRoutePanel },
    { label: 'Intensidade', value: showLegend, onChange: setShowLegend },
    { label: 'Previsão Cronológica', value: showTimeSlider, onChange: setShowTimeSlider },
  ]

  return (
    <div style={{
      position: 'absolute',
      bottom: 20,
      right: 20,
      background: '#000',
      padding: isOpen ? '12px 14px' : '12px',
      borderRadius: '6px',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      zIndex: 5,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '10px',
    }}>
      {isOpen && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {toggles.map((toggle) => (
            <label
              key={toggle.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              <input
                type="checkbox"
                checked={toggle.value}
                onChange={(e) => toggle.onChange(e.target.checked)}
                style={{
                  cursor: 'pointer',
                  width: 18,
                  height: 18,
                  accentColor: '#ff8c1a',
                  flexShrink: 0,
                }}
              />
              <span style={{
                fontSize: 13,
                color: '#fff',
                fontWeight: 400,
              }}>
                {toggle.label}
              </span>
            </label>
          ))}
        </div>
      )}
      
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: 'none',
          border: 'none',
          color: '#ff8c1a',
          cursor: 'pointer',
          fontSize: '18px',
          padding: '0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: '20px',
          transition: 'transform 0.2s',
        }}
        title={isOpen ? 'Esconder detalhes' : 'Mostrar detalhes'}
      >
        {isOpen ? '›' : '‹'}
      </button>
    </div>
  )
}
