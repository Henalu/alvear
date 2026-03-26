# Alvear Offline

Alvear es una capa `offline-first` sobre la idea de MiroFish para ensayar reacciones colectivas antes de lanzar un producto, mensaje o decision. En esta v1 el foco es `backend + CLI`, con `Neo4j` local para el grafo y `Ollama` como proveedor LLM compatible con OpenAI.

## Estado actual

- `MiroFish-main-alvear/` se conserva como referencia upstream de solo lectura.
- El trabajo vivo de Alvear está en `backend/`, `docs/context/`, `seeds/` y `scripts/`.
- El flujo soportado es: `ingest -> build-graph -> prepare -> run -> summarize`.
- La simulacion social usa los runners de OASIS ya portados, pero requiere instalar sus dependencias opcionales.

## Quickstart

1. Crear un entorno virtual y activarlo.
2. Instalar el backend:

```bash
pip install -e ./backend
```

3. Si vas a ejecutar simulaciones OASIS completas, instala también el extra:

```bash
pip install -e "./backend[oasis]"
```

4. Copiar la configuracion local:

```bash
cp .env.example .env
```

5. Levantar Neo4j:

```bash
docker compose -f docker-compose.offline.yml up -d neo4j
```

6. Arrancar Ollama y descargar el modelo por defecto:

```bash
ollama serve
ollama pull qwen2.5:14b
```

7. Flujo base con el seed canónico:

```bash
cd backend
python -m alvear.cli init --name "Product Launch ES" --requirement "Simular la reaccion social a un lanzamiento de producto en espanol."
python -m alvear.cli ingest --project-id <PROJECT_ID> ..\\seeds\\product_launch_es\\launch_brief.md ..\\seeds\\product_launch_es\\landing_copy.md ..\\seeds\\product_launch_es\\faq.md ..\\seeds\\product_launch_es\\sample_reactions.md
python -m alvear.cli build-graph --project-id <PROJECT_ID>
python -m alvear.cli prepare --project-id <PROJECT_ID> --max-entities 24
python -m alvear.cli run --simulation-id <SIMULATION_ID> --platform parallel --max-rounds 12
python -m alvear.cli summarize --simulation-id <SIMULATION_ID>
```

## Estructura

- `backend/`: paquete Python, CLI, servicios offline y scripts OASIS.
- `docs/context/`: contexto canónico para humanos y agentes IA.
- `seeds/product_launch_es/`: escenario base de pruebas.
- `scripts/`: utilidades de smoke y automatización local.
- `MiroFish-main-alvear/`: upstream local, no tocar salvo inspección.

## Lectura recomendada

1. `AGENTS.md`
2. `docs/context/index.md`
3. `docs/context/worklog.md`

## Limitaciones v1

- No hay UI re-integrada todavía.
- El modo `run` depende de tener instaladas las librerías de OASIS/CAMEL.
- Los smoke tests completos requieren servicios locales vivos: `Neo4j` y `Ollama`.
