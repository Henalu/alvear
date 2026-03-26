# Offline Adaptation Spec

## Objetivo

Definir la versión offline mínima viable de Alvear sin depender de servicios cloud obligatorios.

## Proveedor LLM

### Contrato

- proveedor por defecto: `ollama`
- API shape: compatible con OpenAI chat completions
- variables:
  - `LLM_PROVIDER`
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL_NAME`

### Defaults actuales

- `LLM_PROVIDER=ollama`
- `LLM_API_KEY=ollama`
- `LLM_BASE_URL=http://localhost:11434/v1`
- `LLM_MODEL_NAME=qwen2.5:14b`

## Grafo

### Contrato canónico

`GraphStore` debe ofrecer:

- `create_graph`
- `set_ontology`
- `ingest_chunks`
- `get_graph_data`
- `get_all_nodes`
- `get_all_edges`
- `search_graph`
- `append_simulation_memory`

### Implementación v1

`Neo4jGraphStore`

Responsabilidades:

- crear el nodo `Graph`
- persistir ontología y metadata
- persistir `DocumentChunk`
- deduplicar entidades por `entity_type + name`
- guardar relaciones tipadas como `RELATES_TO` con propiedad `name`
- soportar búsqueda `full-text` con fallback keyword
- registrar memoria de simulación en nodos `SimulationMemory`

## Construcción de grafo

### Input

- chunks de texto
- ontología
- metadata de proyecto

### Output

- `graph_id`
- nodos de entidad
- relaciones entre entidades
- `graph_manifest.json` local

### Estrategia v1

- extracción por chunk con LLM
- JSON estricto
- deduplicación por clave normalizada
- sin embeddings en v1

## Lectura de entidades

`ZepEntityReader` es un shim offline.

Responsabilidades:

- listar entidades desde `Neo4jGraphStore`
- enriquecer con relaciones y nodos cercanos
- filtrar por tipos definidos
- limitar el número de agentes en preparación

## Preparación de simulación

Artefactos obligatorios por simulación:

- `state.json`
- `entities_snapshot.json`
- `simulation_config.json`
- `reddit_profiles.json`
- `twitter_profiles.csv`

## Ejecución

Se mantienen los runners heredados:

- `run_parallel_simulation.py`
- `run_twitter_simulation.py`
- `run_reddit_simulation.py`

Precondiciones:

- dependencias OASIS/CAMEL instaladas
- configuración LLM accesible
- directorio de simulación preparado

Artefactos esperados de ejecución:

- `run_state.json`
- `simulation.log`
- `twitter/actions.jsonl`
- `reddit/actions.jsonl`
- SQLite por plataforma

## Resumen

`SummaryGenerator` genera `summary.md` a partir de:

- `simulation_config.json`
- `run_state.json`
- logs JSONL de acciones

## Scope v1

Incluido:

- backend offline
- CLI
- seed canónico
- quickstart local

Pospuesto:

- API HTTP estable
- UI
- búsqueda vectorial
- reportes avanzados narrativos
