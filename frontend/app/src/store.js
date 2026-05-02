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

  origin: [-7.70, 40.28],
  destination: [-7.53, 40.37],

  currentRoute: null,
  previousRoute: null,
  isRerouted: false,

  status: 'idle',
  mode: 'demo',
  selectedFire: null,
  showCompass: true,
  showWindHUD: true,
  showLegend: true,
  showTimeSlider: true,
  showRoutePanel: true,
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
    currentRoute: null,
    previousRoute: null,
    isRerouted: false,
    status: 'idle',
  }),

  setActiveFireInfo: (info) => set({ activeFireInfo: info }),

  setCurrentStep: (step) => set({ currentStep: step }),
  setIsPlaying: (v) => set({ isPlaying: v }),
  setOrigin: (coords) => set({ origin: coords }),
  setDestination: (coords) => set({ destination: coords }),

  setCurrentRoute: (route) => set((state) => ({
    previousRoute: state.currentRoute,
    currentRoute: route,
  })),

  setRerouted: (v) => set({ isRerouted: v }),
  setStatus: (s) => set({ status: s }),
  setMode: (m) => set({ mode: m }),
  setShowCompass: (v) => set({ showCompass: v }),
  setShowWindHUD: (v) => set({ showWindHUD: v }),
  setShowLegend: (v) => set({ showLegend: v }),
  setShowTimeSlider: (v) => set({ showTimeSlider: v }),
  setShowRoutePanel: (v) => set({ showRoutePanel: v }),
  setShowFireDetailsPanel: (v) => set({ showFireDetailsPanel: v }),

  resetReroute: () => set({ previousRoute: null, isRerouted: false }),
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
    currentRoute: null,
    previousRoute: null,
    isRerouted: false,
    status: 'idle',
  }),
}))

export default useStore
