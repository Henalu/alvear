# Implementation Snapshot

Fecha de corte: 2026-03-26

## Qué existe hoy

Alvear ya tiene un backend offline funcional a nivel de estructura, persistencia local y CLI básica.

## Entradas principales

- CLI: `backend/alvear/cli.py`
- Config central: `backend/app/config.py`
- Quickstart humano: `README.md`
- Contrato operativo para agentes: `AGENTS.md`

## Módulos núcleo implementados

### Proyecto y estado

- `backend/app/models/project.py`
- `backend/app/models/task.py`

Responsabilidades actuales:

- crear proyectos
- copiar ficheros al workspace del proyecto
- guardar texto extraído
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
- imports perezosos para que la CLI básica no dependa de que todo el runtime esté instalado

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
- hacer búsqueda `full-text + keyword fallback`
- exponer shims de compatibilidad heredados de Zep

### Simulación

- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/services/simulation_runner.py`
- `backend/app/services/summary_generator.py`
- `backend/app/services/simulation_ipc.py`
- `backend/scripts/run_parallel_simulation.py`
- `backend/scripts/run_twitter_simulation.py`
- `backend/scripts/run_reddit_simulation.py`

Responsabilidades actuales:

- generar perfiles OASIS desde el grafo local
- generar `simulation_config.json`
- preparar directorios de simulación
- ejecutar runners heredados cuando OASIS/CAMEL están instalados
- sintetizar `summary.md`

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

## No verificado todavía en este workspace

- `build-graph` real contra Neo4j vivo
- `prepare` real contra Ollama vivo
- `run` real con OASIS/CAMEL instalados
- `summarize` sobre artefactos de una simulación real

## Dependencias observadas hoy en este workspace

No instaladas en el momento de este corte:

- `openai`
- `neo4j`
- `python-dotenv`
- `oasis`
- `camel`

Esto no invalida la estructura del proyecto, pero sí bloquea los smoke tests completos.

## Artefactos de runtime esperados

### Proyecto

- `backend/uploads/projects/<project_id>/project.json`
- `backend/uploads/projects/<project_id>/files/*`
- `backend/uploads/projects/<project_id>/extracted_text.txt`
- `backend/uploads/projects/<project_id>/chunks.json`
- `backend/uploads/projects/<project_id>/graph_manifest.json`

### Simulación

- `backend/uploads/simulations/<simulation_id>/state.json`
- `backend/uploads/simulations/<simulation_id>/entities_snapshot.json`
- `backend/uploads/simulations/<simulation_id>/simulation_config.json`
- `backend/uploads/simulations/<simulation_id>/reddit_profiles.json`
- `backend/uploads/simulations/<simulation_id>/twitter_profiles.csv`
- `backend/uploads/simulations/<simulation_id>/run_state.json`
- `backend/uploads/simulations/<simulation_id>/summary.md`

## Riesgos técnicos activos

- el runner heredado sigue siendo la parte más frágil del stack por dependencia externa
- la extracción LLM aún necesita validación empírica con el modelo local elegido
- la construcción del grafo usa extracción conservadora por chunk; puede requerir iteración de prompts tras los primeros tests reales
