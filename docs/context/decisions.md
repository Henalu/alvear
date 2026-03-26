# Decisions

Registro append-only de decisiones de arquitectura y enfoque.

## 2026-03-26

### D-001: v1 se construye fuera del upstream

- `MiroFish-main-alvear/` queda como referencia de solo lectura.
- El producto vivo de Alvear se implementa en la raiz del repo.

### D-002: prioridad a `backend + CLI`

- La primera superficie oficial es la CLI.
- La API HTTP y la UI quedan para una fase posterior.

### D-003: stack offline por defecto

- Grafo: `Neo4j` local.
- LLM: `Ollama` por endpoint compatible OpenAI.
- Persistencia de proyecto y simulacion: ficheros locales.

### D-004: mantener contratos heredados cuando abarata la migracion

- Se conservan nombres como `ZepEntityReader` y `ZepGraphMemoryUpdater`.
- En Alvear son adaptadores locales, no clientes cloud.

### D-005: caso canonico de validacion

- El primer escenario oficial de pruebas es `product_launch_es`.
- Cap por defecto: 24 agentes y 12 rondas.

### D-006: busqueda v1 sin embeddings

- La busqueda del grafo en v1 sera `full-text + keyword fallback`.
- La busqueda vectorial se pospone.

### D-007: la CLI basica debe degradar con gracia

- La inspeccion del proyecto y los comandos basicos no deben romperse solo porque falten dependencias de runtime pesado.
- `python-dotenv` y `openai` se importan de forma perezosa donde aporta valor para mantener la CLI utilizable durante setup y debugging.

### D-008: separar compatibilidad de backend base y compatibilidad de simulacion completa

- El backend base de Alvear puede funcionar en `Python 3.14`.
- La ruta completa de simulacion con OASIS/CAMEL se considera, por ahora, una ruta `Python 3.10-3.12`.
- La documentacion y el packaging deben reflejar esa separacion para evitar instalaciones enganosas.

### D-009: evitar reintentos silenciosos del cliente LLM local

- El cliente LLM usa `LLM_MAX_RETRIES=0` por defecto.
- En entorno local priorizamos fallo rapido y controlado frente a esperas largas sin feedback.

### D-010: el pipeline offline debe completar con fallback determinista

- Si el LLM local no responde a tiempo, `build-graph` debe seguir con ontologia y extraccion por reglas.
- Si falla la generacion de perfiles, el resto de agentes pasan a modo rule-based.
- Si falla la configuracion de eventos, se usa un plan de eventos determinista valido para smoke tests.

### D-011: la ruta de simulacion completa se valida en un entorno dedicado

- Se crea un entorno `.venv311` con `Python 3.11` para separar la validacion de OASIS/CAMEL del runtime base en `Python 3.14`.
- Esta ruta se considera hoy la ruta canonicamente valida para `run`.

### D-012: para simulacion local en CPU, un modelo mas ligero tiene prioridad sobre el modelo grande por defecto

- `qwen2.5:14b` sigue siendo un default razonable para pruebas de calidad, pero no es eficiente para smoke tests de simulacion en CPU.
- `qwen2.5:3b` queda validado como candidato practico para `run` local rapido.

### D-013: separar reconciliacion de artefactos y redaccion del entregable

- `SimulationOutputService` es la capa que lee `actions.jsonl`, repara `run_state.json` y sincroniza `state.json`.
- `SummaryGenerator` ya no cuenta eventos tecnicos como si fueran acciones de agentes.
- El entregable v1 se divide en dato estructurado (`report.json`) y capa humana (`report.md`), con `summary.md` como resumen corto.

### D-014: la capa humana no debe distorsionar la verdad operativa

- El informe debe distinguir entre rondas planificadas y rondas realmente ejecutadas.
- La capa de redaccion debe deduplicar evidencias repetidas cuando varios logs repiten el mismo texto.
- Si hay conflicto entre la narrativa y los artefactos operativos, mandan los artefactos reconciliados.
