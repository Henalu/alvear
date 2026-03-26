# Alvear Offline

Alvear es una capa `offline-first` sobre la idea de MiroFish para ensayar reacciones colectivas antes de lanzar un producto, mensaje o decision. En esta fase la superficie oficial es `backend + CLI`, con `Neo4j` local para el grafo y `Ollama` como proveedor LLM compatible con OpenAI.

## Estado actual

- `MiroFish-main-alvear/` se mantiene como referencia upstream de solo lectura.
- El trabajo vivo de Alvear esta en `backend/`, `docs/context/`, `seeds/` y `scripts/`.
- El flujo operativo validado es `ingest -> build-graph -> prepare -> run -> summarize`.
- `summarize` ya no solo escribe `summary.md`: ahora genera `report.json`, `report.md` y reconcilia `run_state.json` y `state.json` desde los artefactos reales de la simulacion.
- La ruta de simulacion completa sigue dependiendo de OASIS/CAMEL y hoy la ruta estable es un entorno `Python 3.11` o `3.12`.
- Ya existe una corrida larga validada de 12 rondas en `.venv311` con `qwen2.5:3b`: `sim_67b05449cbd4`.
- Esa corrida completa genero 10 acciones reales, cerro en `completed` y produjo `summary.md`, `report.json` y `report.md`.

## Quickstart

1. Crear un entorno virtual y activarlo.
2. Instalar el backend:

```bash
pip install -e ./backend
```

3. Si vas a ejecutar simulaciones OASIS completas, instalar tambien el extra:

```bash
pip install -e "./backend[oasis]"
```

Nota:
Ese extra esta pensado para `Python 3.10-3.12`.
El backend base puede vivir en `Python 3.14`, pero para `run` real conviene usar un entorno separado con `Python 3.11` o `3.12`.

4. Copiar la configuracion local:

```bash
cp .env.example .env
```

5. Levantar Neo4j:

```bash
docker compose -f docker-compose.offline.yml up -d neo4j
```

6. Arrancar Ollama y descargar modelos locales:

```bash
ollama serve
ollama pull qwen2.5:14b
ollama pull qwen2.5:3b
```

7. Flujo base con el seed canonico:

```bash
cd backend
python -m alvear.cli init --name "Product Launch ES" --requirement "Simular la reaccion social a un lanzamiento de producto en espanol."
python -m alvear.cli ingest --project-id <PROJECT_ID> ..\\seeds\\product_launch_es\\launch_brief.md ..\\seeds\\product_launch_es\\landing_copy.md ..\\seeds\\product_launch_es\\faq.md ..\\seeds\\product_launch_es\\sample_reactions.md
python -m alvear.cli build-graph --project-id <PROJECT_ID>
python -m alvear.cli prepare --project-id <PROJECT_ID> --max-entities 24 --no-llm-profiles
python -m alvear.cli run --simulation-id <SIMULATION_ID> --platform parallel --max-rounds 12
python -m alvear.cli summarize --simulation-id <SIMULATION_ID>
```

## Salida esperada por simulacion

Artefactos operativos:

- `state.json`
- `entities_snapshot.json`
- `simulation_config.json`
- `reddit_profiles.json`
- `twitter_profiles.csv`
- `run_state.json`
- `simulation.log`
- `twitter/actions.jsonl`
- `reddit/actions.jsonl`
- SQLite por plataforma

Entregables humanos:

- `summary.md`
- `report.json`
- `report.md`

## Notas operativas

- `LLM_MAX_RETRIES=0` evita esperas silenciosas muy largas cuando el modelo local no responde a tiempo.
- Si `build-graph` o la generacion de eventos agotan timeout, Alvear cae a un modo determinista y sigue produciendo artefactos validos de v1.
- Para smoke tests locales, `prepare --no-llm-profiles` es la ruta recomendada.
- Para simulacion local rapida en CPU, `qwen2.5:3b` es hoy el modelo practico validado.
- `inspect --simulation-id ...` y `summarize --simulation-id ...` ahora reparan `run_state.json` y `state.json` usando los logs reales si quedaron obsoletos.
- El reporte humano distingue entre rondas planificadas y rondas realmente ejecutadas para no sobreinterpretar corridas truncadas.
- La validacion larga de 12 rondas ya funciona, pero el runner todavia muestra `APITimeoutError` intermitentes y la muestra resultante puede quedarse corta para conclusiones fuertes.
- Un `report.md` con menos de 20 acciones debe leerse como entregable exploratorio, no como lectura definitiva de mercado.

## Estructura

- `backend/`: paquete Python, CLI, servicios offline y runners OASIS.
- `docs/context/`: contexto canonico para humanos y agentes IA.
- `seeds/product_launch_es/`: escenario base de pruebas.
- `scripts/`: utilidades locales.
- `MiroFish-main-alvear/`: upstream local, solo lectura.

## Lectura recomendada

1. `AGENTS.md`
2. `docs/context/index.md`
3. `docs/context/implementation_snapshot.md`
4. `docs/context/worklog.md`

## Limitaciones v1

- No hay UI re-integrada todavia.
- `run` completo sigue dependiendo de OASIS/CAMEL y de un Python compatible.
- La ruta larga de 12 rondas ya fue validada una vez de extremo a extremo, pero aun no esta cerrada como ruta estable y repetible.
- El informe humano actual es heuristico y esta pensado para entregar una primera lectura ejecutiva, no como analisis final de alta fidelidad.
- La calidad del entregable sigue condicionada por dos factores: volumen real de acciones y limpieza textual de los logs generados por el runner.
