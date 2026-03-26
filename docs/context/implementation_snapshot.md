# Implementation Snapshot

Fecha de corte: 2026-03-26

## Que existe hoy

Alvear ya tiene una base offline funcional con CLI operativa, persistencia local, grafo en Neo4j y una primera capa de entregables humanos para simulaciones.

## Entradas principales

- CLI: `backend/alvear/cli.py`
- Config central: `backend/app/config.py`
- Quickstart humano: `README.md`
- Contrato operativo para agentes: `AGENTS.md`

## Modulos nucleo implementados

### Proyecto y estado

- `backend/app/models/project.py`
- `backend/app/models/task.py`

Responsabilidades actuales:

- crear proyectos
- copiar ficheros al workspace del proyecto
- guardar texto extraido
- guardar chunks
- guardar `graph_manifest.json`
- persistir metadata local de proyecto

### Utilidades

- `backend/app/utils/file_parser.py`
- `backend/app/utils/llm_client.py`
- `backend/app/utils/logger.py`
- `backend/app/services/text_processor.py`

Responsabilidades actuales:

- extraer texto de `md`, `txt` y `pdf`
- chunking local
- cliente LLM con endpoint compatible OpenAI
- imports perezosos para que la CLI basica no dependa de que todo el runtime este instalado

### Grafo offline

- `backend/app/services/graph_store.py`
- `backend/app/services/neo4j_store.py`
- `backend/app/services/graph_builder.py`
- `backend/app/services/ontology_generator.py`
- `backend/app/services/zep_entity_reader.py`
- `backend/app/services/zep_graph_memory_updater.py`

Responsabilidades actuales:

- crear un `Graph` en Neo4j
- guardar chunks y entidades deduplicadas
- guardar relaciones
- hacer busqueda `full-text + keyword fallback`
- exponer shims de compatibilidad heredados de Zep
- degradar a ontologia y extraccion deterministas cuando el LLM local no responde a tiempo

### Simulacion

- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/services/simulation_runner.py`
- `backend/app/services/simulation_output_service.py`
- `backend/app/services/summary_generator.py`
- `backend/app/services/simulation_ipc.py`
- `backend/scripts/run_parallel_simulation.py`
- `backend/scripts/run_twitter_simulation.py`
- `backend/scripts/run_reddit_simulation.py`

Responsabilidades actuales:

- generar perfiles OASIS desde el grafo local
- generar `simulation_config.json`
- preparar directorios de simulacion
- ejecutar runners heredados cuando OASIS/CAMEL estan instalados
- reconciliar `run_state.json` y `state.json` desde `actions.jsonl`
- generar `summary.md`, `report.json` y `report.md`
- pasar a perfiles rule-based cuando el LLM local falla en la primera generacion

## Comandos CLI disponibles

- `init`
- `ingest`
- `build-graph`
- `prepare`
- `run`
- `summarize`
- `inspect`

## Verificado en este workspace

Funciona ya:

- `python -m compileall backend`
- `python -m alvear.cli --help`
- `python -m alvear.cli init ...`
- `python -m alvear.cli inspect --project-id ...`
- `python -m alvear.cli build-graph --project-id proj_054ebe5a3387`
- `python -m alvear.cli prepare --project-id proj_054ebe5a3387 --max-entities 24 --no-llm-profiles`
- `python -m alvear.cli inspect --simulation-id sim_c95136e52da8`
- `python -m alvear.cli summarize --simulation-id sim_c95136e52da8`
- `py -3.11` en entorno dedicado `.venv311`
- `backend/scripts/run_parallel_simulation.py --config ... --max-rounds 1 --no-wait` con `qwen2.5:3b`
- `backend/scripts/run_parallel_simulation.py --config ... --max-rounds 12 --no-wait` con `qwen2.5:3b`
- `python -m alvear.cli inspect --simulation-id sim_67b05449cbd4`
- `python -m alvear.cli summarize --simulation-id sim_67b05449cbd4`

Resultados reales:

- proyecto smoke: `proj_054ebe5a3387`
- grafo validado: `graph_089846d74ba3`
- simulacion preparada: `sim_c95136e52da8`
- entidades utiles preparadas: 8
- primer run real validado: paralelo, 1 ronda, `qwen2.5:3b`
- corrida larga validada: `sim_67b05449cbd4`, paralelo, 12 rondas, `qwen2.5:3b`
- duracion observada de la corrida larga: ~44 minutos en esta maquina
- acciones reales en corrida larga: 10 totales, 8 en Twitter y 2 en Reddit
- acciones reales generadas en `twitter/actions.jsonl` y `reddit/actions.jsonl`
- `run_state.json` reconciliado a `completed`
- `state.json` reconciliado a `completed`
- `report.json` y `report.md` generados a partir de acciones reales
- el informe distingue rondas planificadas vs rondas ejecutadas y deduplica evidencias repetidas
- la corrida larga confirma que el informe humano gana utilidad, pero sigue teniendo muestra pequena y sesgo hacia Twitter

## No verificado todavia en este workspace

- repetibilidad de corridas largas de 12 rondas en esta misma maquina
- mejora de calidad narrativa cuando la muestra supera 20 acciones reales
- estabilizacion del runner frente a timeouts intermitentes durante la corrida larga

## Runtime observado hoy en este workspace

- `openai`, `neo4j` y `python-dotenv` ya estan instalados y funcionando en `Python 3.14`
- el extra `oasis` del paquete ya no falla al instalarse en `Python 3.14`, porque queda acotado por markers
- la ruta completa OASIS sigue bloqueada en `Python 3.14`
- el upstream usa `camel-oasis==0.2.5` y `camel-ai==0.2.78`
- `docker` y `ollama` ya estan visibles en `PATH`
- Neo4j local responde en `localhost:7687` y `localhost:7474`
- Ollama responde en `localhost:11434` con `qwen2.5:14b`
- Ollama tambien tiene `qwen2.5:3b` para pruebas mas rapidas de simulacion
- `LLM_MAX_RETRIES=0` evita esperas acumuladas por reintentos silenciosos
- existe un entorno dedicado `Python 3.11` en `.venv311` con OASIS/CAMEL instalado
- una corrida de 12 rondas con `qwen2.5:3b` completa, pero acumula `APITimeoutError` intermitentes en llamadas al LLM durante el run

## Artefactos de runtime esperados

### Proyecto

- `backend/uploads/projects/<project_id>/project.json`
- `backend/uploads/projects/<project_id>/files/*`
- `backend/uploads/projects/<project_id>/extracted_text.txt`
- `backend/uploads/projects/<project_id>/chunks.json`
- `backend/uploads/projects/<project_id>/graph_manifest.json`

### Simulacion

- `backend/uploads/simulations/<simulation_id>/state.json`
- `backend/uploads/simulations/<simulation_id>/entities_snapshot.json`
- `backend/uploads/simulations/<simulation_id>/simulation_config.json`
- `backend/uploads/simulations/<simulation_id>/reddit_profiles.json`
- `backend/uploads/simulations/<simulation_id>/twitter_profiles.csv`
- `backend/uploads/simulations/<simulation_id>/run_state.json`
- `backend/uploads/simulations/<simulation_id>/summary.md`
- `backend/uploads/simulations/<simulation_id>/report.json`
- `backend/uploads/simulations/<simulation_id>/report.md`

## Riesgos tecnicos activos

- el runner heredado sigue siendo la parte mas fragil del stack por dependencia externa
- `run` ya puede ejecutarse en `.venv311` y la ruta larga de 12 rondas ya quedo validada una vez, pero todavia no esta endurecida
- `qwen2.5:14b` en CPU local supera con frecuencia el timeout de ontologia y de event planning
- la degradacion determinista evita bloqueos, pero no sustituye una validacion LLM real con un modelo mas rapido o una maquina con GPU
- el informe humano actual es una capa heuristica sobre los logs, todavia no una capa narrativa basada en entrevistas o analisis profundo
- la corrida larga observada genero solo 10 acciones reales, lo que limita la confianza del entregable
- los logs del runner todavia pueden arrastrar texto ruidoso o mal normalizado que empobrece `report.md`
