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
- `run_parallel_simulation.py` validado tambien a 12 rondas con `qwen2.5:3b` en `.venv311`
- `inspect --simulation-id sim_67b05449cbd4` y `summarize --simulation-id sim_67b05449cbd4` ejecutados con exito

IDs de referencia del smoke actual:

- `project_id`: `proj_054ebe5a3387`
- `graph_id`: `graph_089846d74ba3`
- `simulation_id`: `sim_c95136e52da8`
- `simulation_id` corrida larga: `sim_67b05449cbd4`

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
- `backend/uploads/simulations/sim_67b05449cbd4/twitter/actions.jsonl`
- `backend/uploads/simulations/sim_67b05449cbd4/reddit/actions.jsonl`
- `backend/uploads/simulations/sim_67b05449cbd4/run_state.json`
- `backend/uploads/simulations/sim_67b05449cbd4/state.json`
- `backend/uploads/simulations/sim_67b05449cbd4/summary.md`
- `backend/uploads/simulations/sim_67b05449cbd4/report.json`
- `backend/uploads/simulations/sim_67b05449cbd4/report.md`

## Verificacion pendiente

- repetir la corrida de 12 rondas para medir estabilidad, no solo exito puntual
- mejorar la riqueza de interacciones para salir de la banda `small` del reporte
- decidir si `qwen2.5:3b` pasa de baseline validado a default operativo de simulacion local
- reducir la frecuencia de timeouts parciales durante `run`

## Siguiente accion recomendada

1. Endurecer `run` frente a `APITimeoutError` intermitentes para que la corrida larga sea repetible.
2. Mejorar la limpieza textual del output para que `report.md` sea mas legible sin tener que interpretar ruido de logs.
3. Repetir una corrida de 12 rondas y comprobar si el reporte supera la banda `small` de muestra.

## Bloqueos conocidos

- `run` sigue dependiendo de OASIS/CAMEL y de un Python compatible
- `qwen2.5:14b` en CPU local agota el timeout para ontologia y para event planning en esta maquina
- el informe humano ya existe, pero su calidad sigue ligada al volumen y riqueza de acciones capturadas
- la corrida larga ya termina, pero sigue sufriendo timeouts parciales del cliente LLM
- la CLI ya reconcilia estado al auditar, pero no hay todavia un monitor persistente externo al runner para runs largos

## Notas operativas

- `LLM_MAX_RETRIES=0` evita reintentos silenciosos que convertian un timeout de 120s en esperas de muchos minutos
- `build-graph` ya no se queda colgado: si falla el LLM, genera una ontologia y una extraccion por reglas
- `prepare` puede completarse de forma fiable con `--no-llm-profiles`
- la primera ejecucion real de simulacion ya salio con `Python 3.11` y `qwen2.5:3b`
- la corrida larga de referencia (`sim_67b05449cbd4`) completo 12 rondas y cerro en `completed`
- esa corrida larga produjo 10 acciones reales: 8 en Twitter y 2 en Reddit
- el informe humano actual separa dato (`report.json`) y redaccion (`report.md`)
- el informe ya distingue rondas planificadas frente a rondas ejecutadas y evita repetir la misma evidencia textual
- una muestra de 10 acciones sigue siendo util para orientacion ejecutiva, pero no para conclusiones firmes

## Criterio para cerrar la siguiente iteracion

La proxima iteracion deberia terminar con esta meta:

- `run` repetible de 12 rondas con menos timeouts, mas de 20 acciones reales y un `report.md` claramente legible para humanos
