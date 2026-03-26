# Decisions

Registro append-only de decisiones de arquitectura y enfoque.

## 2026-03-26

### D-001: v1 se construye fuera del upstream

- `MiroFish-main-alvear/` queda como referencia de solo lectura.
- El producto vivo de Alvear se implementa en la raíz del repo.

### D-002: prioridad a `backend + CLI`

- La primera superficie oficial es la CLI.
- La API HTTP y la UI quedan para una fase posterior.

### D-003: stack offline por defecto

- Grafo: `Neo4j` local.
- LLM: `Ollama` por endpoint compatible OpenAI.
- Persistencia de proyecto y simulación: ficheros locales.

### D-004: mantener contratos heredados cuando abarata la migración

- Se conservan nombres como `ZepEntityReader` y `ZepGraphMemoryUpdater`.
- En Alvear son adaptadores locales, no clientes cloud.

### D-005: caso canónico de validación

- El primer escenario oficial de pruebas es `product_launch_es`.
- Cap por defecto: 24 agentes y 12 rondas.

### D-006: búsqueda v1 sin embeddings

- La búsqueda del grafo en v1 será `full-text + keyword fallback`.
- La búsqueda vectorial se pospone.

### D-007: la CLI básica debe degradar con gracia

- La inspección del proyecto y los comandos básicos no deben romperse solo porque falten dependencias de runtime pesado.
- `python-dotenv` y `openai` se importan de forma perezosa donde aporta valor para mantener la CLI utilizable durante setup y debugging.
