# Test Scenario V1

## Nombre

`product_launch_es`

## Objetivo

Validar el flujo offline de Alvear con un escenario cercano al uso real: reacción social ante el lanzamiento de un producto explicado en español.

## Inputs obligatorios

- `seeds/product_launch_es/launch_brief.md`
- `seeds/product_launch_es/landing_copy.md`
- `seeds/product_launch_es/faq.md`
- `seeds/product_launch_es/sample_reactions.md`

## Configuración objetivo

- máximo 24 agentes
- máximo 12 rondas
- Neo4j local
- Ollama local
- ejecución preferida: `parallel`

## Criterios de aceptación

### Ingesta

- el proyecto se crea
- los archivos se copian al workspace del proyecto
- se extrae texto y se generan chunks

### Grafo

- se genera una ontología útil
- se crea un `graph_id`
- Neo4j contiene nodos y relaciones consultables
- `inspect --graph-id` devuelve estructura con `nodes` y `edges`

### Preparación

- se genera `entities_snapshot.json`
- se generan `reddit_profiles.json` y/o `twitter_profiles.csv`
- se genera `simulation_config.json`
- el estado termina en `ready`

### Ejecución

- los scripts producen `run_state.json`
- aparecen logs de acciones por plataforma
- el runner puede monitorizar progreso

### Resumen

- se genera `summary.md`
- el resumen incluye volumen de acciones y hot topics

## Comandos de referencia

```bash
cd backend
python -m alvear.cli init --name "Product Launch ES" --requirement "Simular la reaccion social a un lanzamiento de producto en espanol."
python -m alvear.cli ingest --project-id <PROJECT_ID> ..\\seeds\\product_launch_es\\launch_brief.md ..\\seeds\\product_launch_es\\landing_copy.md ..\\seeds\\product_launch_es\\faq.md ..\\seeds\\product_launch_es\\sample_reactions.md
python -m alvear.cli build-graph --project-id <PROJECT_ID>
python -m alvear.cli prepare --project-id <PROJECT_ID> --max-entities 24
python -m alvear.cli run --simulation-id <SIMULATION_ID> --platform parallel --max-rounds 12
python -m alvear.cli summarize --simulation-id <SIMULATION_ID>
```

## Riesgos conocidos

- sin dependencias OASIS no se puede ejecutar `run`
- sin modelo cargado en Ollama la extracción LLM fallará
- sin Neo4j vivo el grafo no se construirá
