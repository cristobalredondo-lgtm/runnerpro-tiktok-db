# RunnerPro — TikTok Content Intelligence DB

Base de datos visual de contenido TikTok para RunnerPro (carnada no-demo + vídeos demo de apps).

## Abrir
```bash
python3 -m http.server 8765
# http://127.0.0.1:8765/app.html
```
`app.html` = shell con sidebar (4 vistas). Click en cualquier vídeo → ficha completa: frame, hook, opening_type, escena, texto en pantalla, formato, tema, transcripción + 🎬 storyboard (análisis del vídeo completo).

## Vistas
- **Outliers no-demo** (`no-demo/outliers.html`) — 6.483 outliers carnada
- **Mapa feeders** (`no-demo/all.html`) — 545 perfiles curados
- **Apps spytok** (`index.html`) — 218 apps → outliers demo
- **Vídeos demo** (`demo_outliers.html`) — 1.810 vídeos

## Datos
- `*.js` = payloads (visión + storyboard + transcripts embebidos)
- `*_frames/`, `storyboards/` = imágenes locales
