import { useEffect } from 'react'
import useStore from '@/store'

export default function TimeSlider() {
  const timesteps = useStore((s) => s.timesteps)
  const currentStep = useStore((s) => s.currentStep)
  const isPlaying = useStore((s) => s.isPlaying)
  const setCurrentStep = useStore((s) => s.setCurrentStep)
  const setIsPlaying = useStore((s) => s.setIsPlaying)
  const total = timesteps.length

  useEffect(() => {
    if (!isPlaying) return
    const id = setInterval(() => {
      setCurrentStep((prev) => {
        if (typeof prev !== 'number') return 0
        if (prev >= total) {
          setIsPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, 800)
    return () => clearInterval(id)
  }, [isPlaying, total, setCurrentStep, setIsPlaying])

  const currentTs = timesteps[currentStep - 1]
  const minutesLabel = currentTs ? `T+${currentTs.minutes_elapsed}min` : 'T+0min'

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10"
      style={{ width: 420 }}>
      <div className="bg-black/70 backdrop-blur-md rounded-xl px-5 py-3 border border-white/10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (currentStep >= total && !isPlaying) {
                setCurrentStep(0)
                setTimeout(() => setIsPlaying(true), 50)
              } else {
                setIsPlaying(!isPlaying)
              }
            }}
            className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-black font-bold transition-all duration-200"
            style={{ background: isPlaying ? '#ff8c1a' : '#39ff14' }}
          >
            {isPlaying ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <rect x="1" y="1" width="4" height="12" rx="1"/>
                <rect x="9" y="1" width="4" height="12" rx="1"/>
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
                <path d="M2 1l11 6-11 6V1z"/>
              </svg>
            )}
          </button>

          <div className="flex-1 flex flex-col gap-1">
            <input
              type="range"
              min={0}
              max={total}
              value={currentStep}
              onChange={(e) => {
                setIsPlaying(false)
                setCurrentStep(Number(e.target.value))
              }}
              className="w-full accent-orange-400 cursor-pointer"
              style={{ height: 4 }}
            />
            <div className="flex justify-between text-xs font-mono text-white/60">
              <span>T+0</span>
              {Array.from({ length: total }, (_, i) => (
                <span key={i}>{`T+${(i + 1) * (timesteps[0]?.minutes_elapsed ?? 10)}min`}</span>
              )).slice(-1)}
            </div>
          </div>

          <span className="font-mono text-sm text-orange-400 flex-shrink-0 w-20 text-right">
            {minutesLabel}
          </span>
        </div>
      </div>
    </div>
  )
}
