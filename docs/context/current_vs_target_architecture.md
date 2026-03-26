# Current vs Target Architecture

## Punto de partida: MiroFish

MiroFish aporta un flujo de producto muy valioso:

1. análisis de materiales
2. generación de ontología
3. construcción de grafo
4. preparación de agentes/simulación
5. ejecución dual de OASIS
6. resumen e inspección

También aporta piezas reutilizables:

- parsing de archivos
- chunking
- persistencia de proyecto y simulación
- runners y logging de OASIS
- artefactos de simulación ya estandarizados

## Qué no sirve tal cual para Alvear v1

- dependencia fuerte de `Zep Cloud`
- modelo mental orientado a backend web antes que a CLI
- prompts y defaults poco alineados con un lanzamiento de producto en español
- acoplamiento innecesario entre extracción, búsqueda y memoria de grafo

## Arquitectura objetivo de Alvear v1

### Superficie

- CLI Python como interfaz principal
- backend modular dentro de `backend/`
- API web fina pospuesta para después de estabilizar la CLI

### Flujo

1. `init`
2. `ingest`
3. `build-graph`
4. `prepare`
5. `run`
6. `summarize`
7. `inspect`

### Infraestructura local

- `Neo4j` como store de grafo principal
- `Ollama` como proveedor LLM compatible con OpenAI
- ficheros locales para estado de proyecto y simulación
- runners OASIS reutilizados cuando las dependencias están instaladas

### Adaptadores de compatibilidad

Para no reescribirlo todo a la vez, Alvear mantiene varios nombres heredados:

- `ZepEntityReader`
- `ZepGraphMemoryUpdater`

En Alvear son shims locales apoyados sobre `Neo4jGraphStore`, no clientes de Zep.

## Qué ya está portado a la raíz del repo

- paquete `backend/`
- `ProjectManager`
- `TaskManager`
- `TextProcessor`
- `OntologyGenerator`
- `GraphBuilderService`
- `Neo4jGraphStore`
- `SimulationManager`
- `SummaryGenerator`
- CLI `alvear`

## Qué queda fuera de v1

- UI re-conectada
- reportes avanzados tipo `ReportAgent`
- chat profundo sobre simulaciones
- embeddings y vector search
- observabilidad avanzada
