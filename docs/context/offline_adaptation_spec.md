# Offline Adaptation Spec

## Objetivo

Definir la version offline minima viable de Alvear sin depender de servicios cloud obligatorios.

## Proveedor LLM

### Contrato

- proveedor por defecto: `ollama`
- API shape: compatible con OpenAI chat completions
- variables:
  - `LLM_PROVIDER`
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_MODEL_NAME`
  - `LLM_REQUEST_TIMEOUT_SECONDS`
  - `LLM_MAX_RETRIES`

### Defaults actuales

- `LLM_PROVIDER=ollama`
- `LLM_API_KEY=ollama`
- `LLM_BASE_URL=http://localhost:11434/v1`
- `LLM_MODEL_NAME=qwen2.5:14b`
- `LLM_MAX_RETRIES=0`

### Comportamiento esperado en local

- el cliente no debe hacer reintentos silenciosos largos por defecto
- si el modelo local no responde a tiempo, la CLI debe degradar con un fallback determinista
- el fallback actual cubre ontologia, extraccion de chunks, perfiles y event planning

## Grafo

### Contrato canonico

`GraphStore` debe ofrecer:

- `create_graph`
- `set_ontology`
- `ingest_chunks`
- `get_graph_data`
- `get_all_nodes`
- `get_all_edges`
- `search_graph`
- `append_simulation_memory`

### Implementacion v1

`Neo4jGraphStore`

Responsabilidades:

- crear el nodo `Graph`
- persistir ontologia y metadata
- persistir `DocumentChunk`
- deduplicar entidades por `entity_type + name`
- guardar relaciones tipadas como `RELATES_TO` con propiedad `name`
- soportar busqueda `full-text` con fallback keyword
- registrar memoria de simulacion en nodos `SimulationMemory`

## Construccion de grafo

### Input

- chunks de texto
- ontologia
- metadata de proyecto

### Output

- `graph_id`
- nodos de entidad
- relaciones entre entidades
- `graph_manifest.json` local

### Estrategia v1

- extraccion por chunk con LLM si responde dentro del timeout
- JSON estricto
- deduplicacion por clave normalizada
- sin embeddings en v1
- fallback heuristico si la ruta LLM falla

## Lectura de entidades

`ZepEntityReader` es un shim offline.

Responsabilidades:

- listar entidades desde `Neo4jGraphStore`
- enriquecer con relaciones y nodos cercanos
- filtrar por tipos definidos
- limitar el numero de agentes en preparacion

## Preparacion de simulacion

Artefactos obligatorios por simulacion:

- `state.json`
- `entities_snapshot.json`
- `simulation_config.json`
- `reddit_profiles.json`
- `twitter_profiles.csv`

Comportamiento v1:

- perfiles LLM opcionales
- fallback rule-based tras el primer fallo de perfil si el LLM local va lento
- `prepare --no-llm-profiles` es la ruta recomendada para smoke tests locales

## Ejecucion

Se mantienen los runners heredados:

- `run_parallel_simulation.py`
- `run_twitter_simulation.py`
- `run_reddit_simulation.py`

Precondiciones:

- dependencias OASIS/CAMEL instaladas
- para la ruta OASIS actual, usar `Python 3.10-3.12`
- configuracion LLM accesible
- directorio de simulacion preparado

Artefactos esperados de ejecucion:

- `run_state.json`
- `simulation.log`
- `twitter/actions.jsonl`
- `reddit/actions.jsonl`
- SQLite por plataforma

## Reconciliacion de estado

`SimulationOutputService` es la capa offline de auditoria de artefactos.

Responsabilidades:

- leer `simulation_config.json`, `state.json`, `run_state.json` y `actions.jsonl`
- separar acciones reales de eventos tecnicos
- inferir el estado final del run a partir de los logs si el monitor original dejo `run_state.json` obsoleto
- sincronizar `state.json` con el estado reconciliado

Comportamiento v1:

- `inspect --simulation-id ...` dispara reconciliacion y persiste el resultado
- `summarize --simulation-id ...` usa esa misma capa antes de redactar el informe

## Reporting

Artefactos de salida humana:

- `summary.md`
- `report.json`
- `report.md`

Comportamiento v1:

- `summary.md` es una vista corta
- `report.json` es la fuente estructurada para trazabilidad y futuras capas
- `report.md` es la primera capa ejecutiva legible por humanos
- el informe actual es heuristico y se apoya en acciones reales, hot topics, perfiles y estado reconciliado

## Scope v1

Incluido:

- backend offline
- CLI
- seed canonico
- quickstart local
- fallback determinista para smoke tests
- reconciliacion de estado desde artefactos
- primera capa de informe humano

Pospuesto:

- API HTTP estable
- UI
- busqueda vectorial
- reportes HTML o visualizaciones avanzadas
- capa narrativa profunda basada en entrevistas o analisis semantico mas rico
