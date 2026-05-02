import { create } from 'zustand'

const useStore = create((set) => ({
  ignition: null,
  timesteps: [],
  metadata: null,
  vectors: null,
  environmental_data: null,
  source: 'manual',

  activeFireInfo: null,

  currentStep: 0,
  isPlaying: false,

  status: 'idle',
  mode: 'demo',
  selectedFire: null,
  showCompass: true,
  showWindHUD: true,
  showLegend: true,
  showTimeSlider: true,
  showFireDetailsPanel: true,

  setSimulation: (data) => set({
    ignition: data.ignition,
    timesteps: data.timesteps,
    metadata: data.metadata,
    vectors: data.vectors,
    environmental_data: data.environmental_data,
    source: data.source || 'manual',
    currentStep: 0,
    isPlaying: false,
    status: 'idle',
  }),

  setActiveFireInfo: (info) => set({ activeFireInfo: info }),

  setCurrentStep: (step) => set({ currentStep: step }),
  setIsPlaying: (v) => set({ isPlaying: v }),

  setStatus: (s) => set({ status: s }),
  setMode: (m) => set({ mode: m }),
  setShowCompass: (v) => set({ showCompass: v }),
  setShowWindHUD: (v) => set({ showWindHUD: v }),
  setShowLegend: (v) => set({ showLegend: v }),
  setShowTimeSlider: (v) => set({ showTimeSlider: v }),
  setShowFireDetailsPanel: (v) => set({ showFireDetailsPanel: v }),

  setSelectedFire: (fire) => set({ selectedFire: fire }),

  resetSimulation: () => set({
    ignition: null,
    timesteps: [],
    metadata: null,
    vectors: null,
    environmental_data: null,
    source: 'manual',
    activeFireInfo: null,
    selectedFire: null,
    currentStep: 0,
    isPlaying: false,
    status: 'idle',
  }),
}))

export default useStore
