import { useState } from 'react'
import useStore from '@/store'

export default function LayersToggle() {
  const [isOpen, setIsOpen] = useState(true)
  
  const showCompass = useStore((s) => s.showCompass)
  const showWindHUD = useStore((s) => s.showWindHUD)
  const showTimeSlider = useStore((s) => s.showTimeSlider)
  const showLegend = useStore((s) => s.showLegend)

  const setShowCompass = useStore((s) => s.setShowCompass)
  const setShowWindHUD = useStore((s) => s.setShowWindHUD)
  const setShowTimeSlider = useStore((s) => s.setShowTimeSlider)
  const setShowLegend = useStore((s) => s.setShowLegend)

  const toggles = [
    { label: 'Bússola', value: showCompass, onChange: setShowCompass },
    { label: 'Vento', value: showWindHUD, onChange: setShowWindHUD },
    { label: 'Intensidade', value: showLegend, onChange: setShowLegend },
    { label: 'Previsão', value: showTimeSlider, onChange: setShowTimeSlider },
  ]

  return (
    <div style={{
      position: 'absolute',
      bottom: 20,
      right: 20,
      background: 'rgba(0,0,0,0.7)',
      backdropFilter: 'blur(12px)',
      padding: isOpen ? '12px 14px' : '12px',
      borderRadius: '12px',
      border: '1px solid rgba(255,255,255,0.06)',
      zIndex: 5,
      fontFamily: "'Manrope', system-ui, sans-serif",
      display: 'flex',
      alignItems: 'flex-start',
      gap: '10px',
    }}>
      {isOpen && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
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
                  width: 16,
                  height: 16,
                  accentColor: '#ef4444',
                  flexShrink: 0,
                  borderRadius: '4px',
                }}
              />
              <span style={{
                fontSize: 13,
                color: 'rgba(255,255,255,0.65)',
                fontWeight: 500,
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
          color: '#ef4444',
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
