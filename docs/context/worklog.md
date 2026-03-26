# Worklog

## Estado actual

Fecha de corte: 2026-03-26

El repo ya tiene una base operativa de Alvear offline:

- estructura raiz creada para `backend/`, `docs/context/`, `seeds/` y `scripts/`
- modulos reutilizables portados desde MiroFish
- configuracion offline centralizada en `backend/app/config.py`
- `LLMClient` compatible con Ollama
- abstraccion `GraphStore` y adaptador `Neo4jGraphStore`
- `OntologyGenerator` y `GraphBuilderService` reescritos para v1 offline
- `ZepEntityReader` y `ZepGraphMemoryUpdater` convertidos en shims locales
- `OasisProfileGenerator`, `SimulationConfigGenerator`, `SimulationManager`, `SimulationOutputService` y `SummaryGenerator` integrados
- CLI `alvear` con comandos `init`, `ingest`, `build-graph`, `prepare`, `run`, `summarize`, `inspect`
- quickstart, `.env.example`, compose offline y seed canonico creados
- snapshot tecnico documentado en `docs/context/implementation_snapshot.md`

## Verificacion realizada

- `python -m compileall backend` ejecutado con exito el 2026-03-26
- `python -m alvear.cli --help` ejecutado con exito desde `backend/`
- `python -m pip install -e ./backend` ejecutado con exito el 2026-03-26
- `python -m pip install -e "./backend[oasis]"` ya no rompe en `Python 3.14` tras ajustar markers del extra
- `init` + `ingest` del seed `product_launch_es` ejecutados con exito en `proj_054ebe5a3387`
- Neo4j local levantado con `docker compose -f docker-compose.offline.yml up -d neo4j`
- Ollama local validado en `localhost:11434` con `qwen2.5:14b`
- `build-graph` validado de extremo a extremo sobre `proj_054ebe5a3387`
- `prepare --no-llm-profiles` validado de extremo a extremo sobre `proj_054ebe5a3387`
- entorno `.venv311` creado con `Python 3.11`
- stack `camel-ai` + `camel-oasis` instalado en `.venv311`
- `run_parallel_simulation.py` validado con `qwen2.5:3b`, `--max-rounds 1` y `--no-wait`
- `inspect --simulation-id sim_c95136e52da8` ahora reconcilia `run_state.json` y `state.json`
- `summarize --simulation-id sim_c95136e52da8` ahora genera `summary.md`, `report.json` y `report.md`
- pasada de deuda tecnica hecha sobre la capa nueva de reporting antes de la corrida larga

IDs de referencia del smoke actual:

- `project_id`: `proj_054ebe5a3387`
- `graph_id`: `graph_089846d74ba3`
- `simulation_id`: `sim_c95136e52da8`

Artefactos reales de ejecucion ya observados:

- `backend/uploads/simulations/sim_c95136e52da8/twitter/actions.jsonl`
- `backend/uploads/simulations/sim_c95136e52da8/reddit/actions.jsonl`
- `backend/uploads/simulations/sim_c95136e52da8/twitter_simulation.db`
- `backend/uploads/simulations/sim_c95136e52da8/reddit_simulation.db`
- `backend/uploads/simulations/sim_c95136e52da8/run_state.json`
- `backend/uploads/simulations/sim_c95136e52da8/state.json`
- `backend/uploads/simulations/sim_c95136e52da8/summary.md`
- `backend/uploads/simulations/sim_c95136e52da8/report.json`
- `backend/uploads/simulations/sim_c95136e52da8/report.md`

## Verificacion pendiente

- ejecucion completa de `run` a 12 rondas
- comprobar como se comporta el informe humano con una simulacion mas rica en interacciones, no solo con 2 posts semilla
- decidir si `qwen2.5:3b` pasa a ser el modelo rapido recomendado por defecto para simulacion local

## Siguiente accion recomendada

1. Ejecutar una corrida de 12 rondas con `qwen2.5:3b` en `.venv311`.
2. Evaluar el `report.json` y `report.md` resultantes para decidir si hace falta una segunda capa de sintesis o entrevistas.
3. Solo despues de eso, decidir si conviene promocionar `qwen2.5:3b` a default operativo para simulacion local.

## Bloqueos conocidos

- `run` sigue dependiendo de OASIS/CAMEL y de un Python compatible
- `qwen2.5:14b` en CPU local agota el timeout para ontologia y para event planning en esta maquina
- el informe humano ya existe, pero su calidad sigue ligada al volumen y riqueza de acciones capturadas
- la CLI ya reconcilia estado al auditar, pero no hay todavia un monitor persistente externo al runner para runs largos

## Notas operativas

- `LLM_MAX_RETRIES=0` evita reintentos silenciosos que convertian un timeout de 120s en esperas de muchos minutos
- `build-graph` ya no se queda colgado: si falla el LLM, genera una ontologia y una extraccion por reglas
- `prepare` puede completarse de forma fiable con `--no-llm-profiles`
- la primera ejecucion real de simulacion ya salio con `Python 3.11` y `qwen2.5:3b`
- el informe humano actual separa dato (`report.json`) y redaccion (`report.md`)
- el informe ya distingue rondas planificadas frente a rondas ejecutadas y evita repetir la misma evidencia textual

## Criterio para cerrar la siguiente iteracion

La proxima iteracion deberia terminar con esta meta:

- `run` estable de 12 rondas con artefactos completos y un `report.md` util para lectura humana
