export default function Legend() {
  const stops = [
    { label: 'Baixa', color: '#ffe066' },
    { label: 'Média', color: '#ff8c1a' },
    { label: 'Alta',  color: '#e63946' },
    { label: 'Extrema', color: '#7a0e0e' },
  ]

  return (
    <div className="absolute bottom-6 right-4 z-10">
      <div className="bg-black/70 backdrop-blur-md rounded-xl p-3 border border-white/5">
        <div className="text-[11px] font-semibold text-white/35 mb-2 tracking-[0.15em] uppercase">Intensidade</div>
        <div className="flex flex-col gap-1.5">
          {stops.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: color }} />
              <span className="text-xs text-white/60">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
