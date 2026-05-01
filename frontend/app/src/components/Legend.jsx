export default function Legend() {
  const stops = [
    { label: 'Baixa', color: '#ffe066' },
    { label: 'Média', color: '#ff8c1a' },
    { label: 'Alta',  color: '#e63946' },
    { label: 'Extrema', color: '#7a0e0e' },
  ]

  return (
    <div className="absolute bottom-24 right-4 z-10">
      <div className="bg-black/70 backdrop-blur-md rounded-xl p-3 border border-white/10">
        <div className="text-xs font-mono text-white/50 mb-2 tracking-widest uppercase">Intensidade</div>
        <div className="flex flex-col gap-1">
          {stops.map(({ label, color }) => (
            <div key={label} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: color }} />
              <span className="text-xs text-white/70 font-sans">{label}</span>
            </div>
          ))}
        </div>
        <div className="mt-2 border-t border-white/10 pt-2 flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 rounded" style={{ background: '#39ff14' }} />
            <span className="text-xs text-white/70">Rota OK</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 rounded" style={{ background: '#ff2e2e', borderTop: '1px dashed #ff2e2e' }} />
            <span className="text-xs text-white/70">Rota cortada</span>
          </div>
        </div>
      </div>
    </div>
  )
}
