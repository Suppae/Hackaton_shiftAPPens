import useStore from '@/store'

export default function LayersToggle() {
  const showCompass = useStore((s) => s.showCompass)
  const showTimeSlider = useStore((s) => s.showTimeSlider)
  const showRoutePanel = useStore((s) => s.showRoutePanel)
  const showFireDetailsPanel = useStore((s) => s.showFireDetailsPanel)

  const setShowCompass = useStore((s) => s.setShowCompass)
  const setShowTimeSlider = useStore((s) => s.setShowTimeSlider)
  const setShowRoutePanel = useStore((s) => s.setShowRoutePanel)
  const setShowFireDetailsPanel = useStore((s) => s.setShowFireDetailsPanel)

  const toggles = [
    { label: 'Bussola', value: showCompass, onChange: setShowCompass },
    { label: 'Wildfire Routing', value: showRoutePanel, onChange: setShowRoutePanel },
    { label: 'Intensidade', value: showFireDetailsPanel, onChange: setShowFireDetailsPanel },
    { label: 'Previsão Cronológica', value: showTimeSlider, onChange: setShowTimeSlider },
  ]

  return (
    <div style={{
      position: 'absolute',
      bottom: 20,
      right: 20,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      zIndex: 5,
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
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
            color: '#333',
            fontWeight: 400,
          }}>
            {toggle.label}
          </span>
        </label>
      ))}
    </div>
  )
}
