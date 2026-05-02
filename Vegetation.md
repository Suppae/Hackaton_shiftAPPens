# 🌍 EarthEngineCLCProvider — APIs, Pipeline e Output

## 📌 Visão Geral

O `EarthEngineCLCProvider` é um serviço de processamento geoespacial que utiliza o Google Earth Engine para gerar um **mapa de risco de incêndio baseado em vegetação**.

Ele transforma um **polígono geográfico** num **grid 2D (NumPy array)** onde cada célula representa o risco relativo de propagação de fogo.

---

# 🔌 APIs / Datasets Utilizados

## 🌲 CORINE Land Cover (CLC)
Google Earth Engine dataset:
- CORINE Land Cover (Copernicus)

Função:
- Define o tipo de uso do solo (floresta, urbano, água, etc.)
- Base estrutural do combustível

Saída:
- Raster com códigos discretos (ex: 311 floresta, 111 urbano)

---

## 🌱 NDVI (Vegetação viva)
MODIS NDVI:
:contentReference[oaicite:0]{index=0}

Função:
- Mede vigor e densidade da vegetação
- Proxy de biomassa viva

Saída:
- Valores normalizados (~0 a 1 após scaling)

---

## 💧 NDMI (Humidade da vegetação)
MODIS NDMI:
:contentReference[oaicite:1]{index=1}

Função:
- Estima humidade da vegetação
- Indica stress hídrico

Saída:
- Proxy de secura do combustível

---

## 🌳 LAI (Leaf Area Index)
MODIS LAI:
:contentReference[oaicite:2]{index=2}

Função:
- Mede densidade de folhas
- Representa carga de combustível vertical

Saída:
- Valor contínuo de densidade vegetal

---


| Valor     | Interpretação  | Comportamento do fogo   |
| --------- | -------------- | ----------------------- |
| 0.0       | Não inflamável | fogo não propaga        |
| 0.1 – 0.5 | Baixo risco    | propagação lenta        |
| 0.5 – 1.0 | Moderado       | propagação normal       |
| 1.0 – 2.0 | Alto risco     | propagação rápida       |
| > 2.0     | Extremo        | comportamento explosivo |


# ⚙️ Pipeline de Processamento

## 1. Entrada

O sistema recebe:

```python
polygon = [(lon, lat), (lon, lat), ...]