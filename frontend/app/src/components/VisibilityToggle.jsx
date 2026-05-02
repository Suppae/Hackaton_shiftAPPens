import useStore from '@/store'

export default function VisibilityToggle() {
  const showCompass = useStore((s) => s.showCompass)
  const showWindHUD = useStore((s) => s.showWindHUD)
  const showLegend = useStore((s) => s.showLegend)
  const showTimeSlider = useStore((s) => s.showTimeSlider)
  
  const setShowCompass = useStore((s) => s.setShowCompass)
  const setShowWindHUD = useStore((s) => s.setShowWindHUD)
  const setShowLegend = useStore((s) => s.setShowLegend)
  const setShowTimeSlider = useStore((s) => s.setShowTimeSlider)

  const toggles = [
    { label: 'Bússola', value: showCompass, onChange: setShowCompass },
    { label: 'Vento', value: showWindHUD, onChange: setShowWindHUD },
    { label: 'Tempo', value: showTimeSlider, onChange: setShowTimeSlider },
    { label: 'Legenda', value: showLegend, onChange: setShowLegend },
  ]

  return (
    <div style={{
      position: 'absolute',
      bottom: 20,
      right: 20,
      display: 'grid',
      gridTemplateColumns: 'repeat(2, 1fr)',
      gap: 10,
      zIndex: 5,
    }}>
      {toggles.map((toggle) => (
        <label
          key={toggle.label}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '8px 10px',
            background: 'rgba(10,10,10,0.85)',
            border: '1px solid rgba(255,140,26,0.3)',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 12,
            color: '#fff',
            fontFamily: 'Inter, sans-serif',
            whiteSpace: 'nowrap',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,140,26,0.6)'
            e.currentTarget.style.background = 'rgba(10,10,10,0.95)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,140,26,0.3)'
            e.currentTarget.style.background = 'rgba(10,10,10,0.85)'
          }}
        >
          <input
            type="checkbox"
            checked={toggle.value}
            onChange={(e) => toggle.onChange(e.target.checked)}
            style={{
              width: 16,
              height: 16,
              accentColor: '#ff8c1a',
              cursor: 'pointer',
              margin: 0,
            }}
          />
          <span>{toggle.label}</span>
        </label>
      ))}
    </div>
  )
}
