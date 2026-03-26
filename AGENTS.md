# AGENTS.md

Este repo usa un hub canónico de contexto. Antes de hacer cambios, cualquier agente debe leer en este orden:

1. `README.md`
2. `docs/context/index.md`
3. `docs/context/implementation_snapshot.md`
4. `docs/context/worklog.md`
5. `docs/context/decisions.md`

## Reglas operativas

- `MiroFish-main-alvear/` es referencia upstream de solo lectura.
- El producto vivo de Alvear se construye en la raiz del repo, no dentro del upstream.
- La v1 es `offline-first`: nada debe depender de Zep Cloud ni de APIs externas obligatorias.
- El stack objetivo actual es `Neo4j local + Ollama + backend/CLI`.
- Mantener compatibilidad de artefactos con OASIS: `state.json`, `simulation_config.json`, `reddit_profiles.json`, `twitter_profiles.csv`, `run_state.json`, logs y SQLite.
- Documentar decisiones nuevas en `docs/context/decisions.md`.
- Actualizar el estado real en `docs/context/worklog.md` al cerrar una iteración relevante.

## Convenciones de implementación

- Preferir reutilizar módulos portados desde MiroFish si no rompen el modo offline.
- Mantener los adaptadores de compatibilidad `zep_*` como shims locales mientras existan importaciones heredadas.
- Usar `backend/alvear/cli.py` como superficie principal de v1.
- El seed de referencia es `seeds/product_launch_es/`.

## Qué no hacer

- No reintroducir dependencias de Zep Cloud.
- No convertir `MiroFish-main-alvear/` en el workspace activo del producto.
- No asumir que la UI existe o que es prioritaria en esta fase.
