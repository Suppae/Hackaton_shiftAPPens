# Hackathon Project: Dynamic Wildfire Routing — Frontend (React)

## 1. Contexto e Objetivo (48h Hackathon)
MVP de um sistema que prevê propagação de incêndio florestal e recalcula
dinamicamente rotas de emergência, bloqueando estradas que cruzam a frente
de fogo.

**Eu sou o Lead de Frontend.** O backend (FastAPI) já existe e expõe um
endpoint que devolve a propagação do fogo como GeoJSONs iterativos.
Este documento define a aplicação React.

**Prioridade Máxima:** impacto visual na demo + interactividade. Zero
over-engineering. Tempo é a única métrica que conta.

---

## 2. Tech Stack (decidida — não discutir)
- **Build:** Vite + React 18 (JSX, **sem TypeScript** — overhead a mais para 48h)
- **Mapa:** `react-map-gl` v7 + `mapbox-gl` v3
- **Estilos:** Tailwind CSS via CDN (sem PostCSS, sem build step extra)
- **Estado:** Zustand (1 ficheiro, ~50 linhas) — evita prop drilling
- **HTTP:** `fetch` nativo. Sem axios.
- **Routing:** Mapbox Directions API (`/directions/v5/mapbox/driving`)
  com parâmetro `exclude` para evitar polígonos do fogo
- **Token Mapbox:** `import.meta.env.VITE_MAPBOX_TOKEN` (em `.env.local`)

---

## 3. Backend Contract (este é o input — tratar como sagrado)

Backend corre em `http://localhost:8000` em dev.

### Endpoints
| Método | Path              | Quando usar                                    |
|--------|-------------------|-----------------------------------------------|
| POST   | `/simulate`       | Ignição custom (click no mapa, sliders, etc.) |
| GET    | `/simulate/demo`  | Cenário pré-fabricado para a demo ao vivo     |

### Forma da resposta
```jsonc
{
  "ignition": [-7.6167, 40.3217],            // [lon, lat]
  "metadata": {
    "engine": "mock",                         // "mock" agora, "ca" depois
    "wind_speed_ms": 8.0,
    "wind_direction_deg": 225.0,              // FROM, clockwise from N
    "humidity_pct": 25.0,
    "n_steps": 6,
    "minutes_per_step": 10
  },
  "timesteps": [
    {
      "t": 1,
      "minutes_elapsed": 10,
      "burned_area": {
        "type": "Feature",
        "properties": { "timestep": 1, "minutes": 10, "intensity": 0.166 },
        "geometry": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] }
      }
    }
    // ... t=2 ... t=N
  ]
}
```

Cada `burned_area` é um GeoJSON `Feature` válido — vai direto para uma
source do Mapbox sem transformação. Nunca mexer no shape; se algo não
encaixa, mexer no backend, não no frontend.

### Body do POST /simulate
```jsonc
{
  "ignition_lon": -8.6291,
  "ignition_lat": 41.1579,
  "n_steps": 6,                  // opcional, default 6
  "minutes_per_step": 10,        // opcional, default 10
  "wind_speed_ms": 12.0,         // opcional — se omitido, backend usa OWM
  "wind_direction_deg": 0.0,     // opcional
  "humidity_pct": 20.0           // opcional
}
```

---

## 4. Setup do Mapa (decisões já tomadas)

```js
const INITIAL_VIEW = {
  longitude: -7.6167,
  latitude: 40.3217,
  zoom: 11,
  pitch: 45,        // 3D ligado desde o segundo zero
  bearing: 0,
};

const MAP_STYLE = "mapbox://styles/mapbox/satellite-streets-v12";
// Alternativa: "mapbox://styles/mapbox/dark-v11" para o toggle
```

**Terreno 3D:** ao montar o mapa, adicionar source `mapbox-dem`
(`raster-dem`, tilesize 512, maxzoom 14) e chamar `map.setTerrain({
source: 'mapbox-dem', exaggeration: 1.5 })`. Adicionar `sky` layer para o
horizonte ficar bonito em pitch alto.

---

## 5. Árvore de Componentes

```
src/
├── App.jsx                  # composição + layout
├── store.js                 # Zustand: ignition, timesteps, currentStep, route, status
├── api/
│   ├── backend.js           # fetchSimulation(), fetchDemo()
│   └── mapbox.js            # fetchRoute(origin, dest, excludePolygons)
├── components/
│   ├── MapView.jsx          # <Map> + setup terreno + handlers de click
│   ├── FireLayer.jsx        # <Source>+<Layer> animados pelo currentStep
│   ├── RouteLayer.jsx       # rota verde + rota antiga vermelha tracejada
│   ├── MarkersLayer.jsx     # pin de origem, destino, ignição
│   ├── TimeSlider.jsx       # play/pause + slider 0..n_steps
│   ├── WindHUD.jsx          # seta + m/s + humidade (canto superior direito)
│   ├── StatsPanel.jsx       # área ardida, ETA, distância (canto inferior esq)
│   ├── ScenarioPicker.jsx   # botões "Pedrógão", "Serra da Estrela", "Custom"
│   └── Legend.jsx           # legenda de cores (timestep → cor)
└── utils/
    ├── geometry.js          # routeIntersectsFire(routeGeoJSON, fireGeoJSON)
    └── format.js            # km², HH:MM, etc.
```

---

## 6. Features (priorizadas — não desviar para outras coisas)

### Core (obrigatório, é a história da demo)
1. **Mapa satélite com terreno 3D** (pitch 45°, exaggeration 1.5)
2. **Camada de fogo animada** — gradient amarelo→laranja→vermelho conforme
   `properties.intensity`; renderizar **todos os timesteps até** `currentStep`
   com opacidade decrescente (T+1 mais transparente, T+N mais opaco) para
   sugerir progressão
3. **Glow nas bordas** — `line-blur: 3` + animação de `line-opacity`
   (loop 0.6 ↔ 1.0 a 1.5s) para parecer brasa viva
4. **Time slider com play/pause** — `setInterval` a 800ms entre passos
5. **Origem e Destino dragáveis** — pins customizados (verde, azul)
6. **Rota verde néon** via Mapbox Directions
7. **Re-routing automático**: depois de cada novo timestep, verificar se a
   rota actual intersecta algum polígono de fogo (Turf.js
   `booleanIntersects` ou implementação ingénua); se sim:
   - Manter a rota antiga visível, **vermelha tracejada** (`line-dasharray`)
   - Pedir nova rota com `exclude=polygon(...)` (Mapbox aceita até 3 polígonos)
   - Desenhar nova rota verde por cima
8. **Painel de stats** (canto inferior esquerdo): área ardida (km²),
   distância da rota (km), ETA (min), badge "REROUTED" quando aplicável

### High-leverage (entram no MVP)
9. **HUD de vento** (canto sup. dir.): seta SVG rodada conforme
   `wind_direction_deg`, label com `wind_speed_ms` e `humidity_pct`.
   Animação subtil de pulso na ponta da seta.
10. **Cenários pré-feitos** (`ScenarioPicker.jsx`):
    - "Pedrógão Grande" → ignição (-8.140, 40.045), vento SO
    - "Serra da Estrela" → endpoint `/simulate/demo`
    - "Custom" → ativa modo "click no mapa para ignir"
11. **Click-to-ignite** quando em modo Custom: dispara `POST /simulate`
    com as coordenadas do click

### Nice-to-have (só se sobrar tempo, não começar isto antes do core)
12. Toggle satélite ↔ dark
13. Pluma de fumo (polígono semitransparente cinza, alongado a jusante
    do vento, intensidade derivada do timestep mais recente)
14. POIs de evacuação (hospitais via Overpass API:
    `node["amenity"="hospital"](bbox)`)
15. Som ambiente subtil quando a rota é cortada

---

## 7. Visual Style (referência — não inventar)
- **Fundo:** mapa em satélite escuro (à noite no mapbox satellite-streets
  fica naturalmente dramático); painéis em `bg-black/60 backdrop-blur-md`
- **Cores principais:**
  - Fogo: gradient `#ffe066` → `#ff8c1a` → `#e63946` → `#7a0e0e`
  - Rota OK: `#39ff14` (verde néon)
  - Rota cortada: `#ff2e2e` tracejada
  - Origem: `#39ff14`, Destino: `#22d3ee`
- **Texto:** `font-mono` para stats (parece dashboard de controlo);
  `font-sans` para tudo o resto
- **Animações:** transitions de 200ms, `ease-out`. Nada de bouncy ou cute.

---

## 8. Regras Estritas para o LLM (Claude Code)

1. **Hackathon mode:** se houver caminho 5x mais rápido com 90% do
   resultado visual, escolher esse. Confirmar antes só se for ambíguo.
2. **Sem TypeScript.** Sem testes unitários. Sem Storybook. Sem ESLint
   custom. Sem Husky.
3. **Tailwind via CDN** (`<script src="https://cdn.tailwindcss.com">` no
   `index.html`). Não setup PostCSS.
4. **Mock fallback obrigatório:** todas as chamadas a backend devem ter
   `try/catch` que cai num mock hardcoded. Se o backend cair às 4h da
   manhã, a demo continua. Concretamente: importar um JSON de exemplo
   em `src/api/mockData.json` (gerar uma vez com
   `curl localhost:8000/simulate/demo > mockData.json`).
5. **Mock fallback aplica-se também à Mapbox Directions API** — se 401
   ou rate limit, devolver uma `LineString` em linha recta entre origem e
   destino para a demo não morrer.
6. **Nunca usar OpenWeatherMap v3.0 (OneCall).** Só v2.5 (`/data/2.5/weather`).
   Isto está implementado no backend; o frontend só lê `metadata`.
7. **Nada de SSR**, nada de Next.js. Vite + SPA.
8. **Não criar componentes "para o futuro"** que ainda não estão na
   árvore da secção 5. Se faltar algo, perguntar antes de inventar.
9. **Imports absolutos via alias `@/`** (configurar no `vite.config.js`).
10. **Commits pequenos**, mensagens em inglês, prefixo `feat:`/`fix:`/`chore:`.

---

## 9. Estado actual

**Feito:**
- Backend FastAPI a correr em `localhost:8000`
- Endpoints `/simulate` e `/simulate/demo` testados
- Mock engine produz elipses orientadas pelo vento, área cresce
  monotonicamente

**A fazer (ordem sugerida):**
1. `npm create vite@latest frontend -- --template react`, instalar deps
2. Setup Mapbox token + estilo de mapa + terreno 3D → ver isto a
   funcionar antes de avançar
3. Store Zustand com shape da resposta do backend
4. `MapView` + `FireLayer` consumindo `/simulate/demo` (hardcoded por agora)
5. `TimeSlider` + animação dos timesteps
6. `MarkersLayer` (origem/destino dragáveis) + `RouteLayer` (rota inicial)
7. Detecção de intersecção rota↔fogo + re-routing
8. `WindHUD` + `StatsPanel`
9. `ScenarioPicker` + click-to-ignite
10. Polish visual: glow, gradients, transitions

---

## 10. Demo Script (o que o juiz vai ver em 60 segundos)

1. Abrir app → mapa 3D satélite na Serra da Estrela, terreno visível
2. Clicar "Pedrógão Grande" no `ScenarioPicker`
3. Mapa voa para a localização, dois pins (origem/destino) já posicionados,
   rota verde traçada
4. HUD de vento mostra "8 m/s SO, 25% HR"
5. Carregar PLAY → fogo começa a crescer, intensidade aumenta, glow pulsa
6. Ao timestep T+3: rota intersecta fogo → fica vermelha tracejada,
   badge "REROUTED" aparece, nova rota verde aparece a contornar
7. `StatsPanel` actualiza: "47.3 km² ardidos | Rota +12 min | ETA 23min"
8. Juiz: 🤯
