# Worklog

## Estado actual

Fecha de corte: 2026-03-26

El repo ya tiene una base operativa de Alvear offline:

- estructura raíz creada para `backend/`, `docs/context/`, `seeds/` y `scripts/`
- módulos reutilizables portados desde MiroFish
- configuración offline centralizada en `backend/app/config.py`
- `LLMClient` compatible con Ollama
- abstracción `GraphStore` y adaptador `Neo4jGraphStore`
- `OntologyGenerator` y `GraphBuilderService` reescritos para v1 offline
- `ZepEntityReader` y `ZepGraphMemoryUpdater` convertidos en shims locales
- `OasisProfileGenerator`, `SimulationConfigGenerator`, `SimulationManager` y `SummaryGenerator` ya integrados
- CLI `alvear` con comandos `init`, `ingest`, `build-graph`, `prepare`, `run`, `summarize`, `inspect`
- quickstart, `.env.example`, compose offline y seed canónico creados
- snapshot técnico documentado en `docs/context/implementation_snapshot.md`

## Verificación realizada

- `python -m compileall backend` ejecutado con éxito el 2026-03-26
- `python -m alvear.cli --help` ejecutado con éxito desde `backend/`
- `python -m alvear.cli init ...` ejecutado con éxito el 2026-03-26
- `python -m alvear.cli inspect --project-id ...` ejecutado con éxito el 2026-03-26

## Verificación pendiente

- smoke test real contra `Neo4j` local
- smoke test real contra `Ollama`
- `build-graph` real con extracción LLM y persistencia en Neo4j
- `prepare` real con generación de perfiles y `simulation_config.json`
- ejecución completa de `run` con dependencias OASIS instaladas

## Siguiente acción recomendada

1. Instalar dependencias Python del backend.
2. Levantar Neo4j con `docker compose -f docker-compose.offline.yml up -d neo4j`.
3. Arrancar Ollama y descargar el modelo definido en `.env`.
4. Ejecutar el flujo completo del seed `product_launch_es`.

## Bloqueos conocidos

- este workspace no tiene instaladas todas las dependencias Python de runtime
- dependencias ausentes observadas en este corte: `openai`, `neo4j`, `python-dotenv`, `oasis`, `camel`
- no se ha validado todavía la conexión real con servicios locales
- `run` sigue dependiendo de librerías externas de OASIS/CAMEL

## Notas operativas

- la CLI básica sí arranca sin todas las dependencias gracias a imports perezosos
- esto permite inspeccionar el proyecto y preparar el entorno antes de instalar todo el runtime

## Criterio para cerrar la siguiente iteración

La próxima iteración debería terminar con:

- un `project_id` y `graph_id` reales creados
- una simulación preparada con artefactos válidos
- si es posible, una ejecución real y `summary.md`
