# Upstream Provenance

## Referencia upstream

Repositorio local de referencia:

- `MiroFish-main-alvear/`

Uso permitido dentro de este repo:

- lectura
- inspección de arquitectura
- portado selectivo de módulos

Uso no permitido por convención interna:

- editar el upstream como si fuera el producto vivo de Alvear

## Ficheros portados inicialmente desde MiroFish

Copiados al inicio del arranque offline y luego adaptados:

- `backend/app/models/project.py`
- `backend/app/models/task.py`
- `backend/app/utils/file_parser.py`
- `backend/app/utils/llm_client.py`
- `backend/app/utils/logger.py`
- `backend/app/utils/retry.py`
- `backend/app/services/text_processor.py`
- `backend/app/services/ontology_generator.py`
- `backend/app/services/simulation_config_generator.py`
- `backend/app/services/oasis_profile_generator.py`
- `backend/app/services/simulation_manager.py`
- `backend/app/services/simulation_runner.py`
- `backend/app/services/simulation_ipc.py`
- `backend/scripts/run_parallel_simulation.py`
- `backend/scripts/run_reddit_simulation.py`
- `backend/scripts/run_twitter_simulation.py`
- `backend/scripts/action_logger.py`

## Adaptaciones realizadas sobre el portado

- eliminación de dependencia efectiva de Zep Cloud
- sustitución por `Neo4jGraphStore`
- sustitución por `LLMClient` compatible con Ollama
- simplificación y reorientación al escenario de lanzamiento de producto
- incorporación de una CLI como superficie principal

## Shims de compatibilidad

Para evitar reescrituras grandes en una sola iteración, estos nombres heredados se conservan:

- `ZepEntityReader`
- `ZepGraphMemoryUpdater`

Ambos apuntan ahora a implementaciones locales.

## Nota de distribución

Antes de cualquier distribución comercial o pública más amplia, revisar:

- licencia y atribución del upstream original
- grado exacto de reutilización de código
- necesidad de documentar modificaciones de forma más formal
