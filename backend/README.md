# Backend Alvear

Paquete Python del backend offline de Alvear.

## Instalar

```bash
pip install -e .
```

Con dependencias de simulacion:

```bash
pip install -e ".[oasis]"
```

La ruta OASIS/CAMEL requiere actualmente `Python < 3.13`.

## CLI

```bash
python -m alvear.cli --help
```

## Nota de runtime local

- `LLM_MAX_RETRIES=0` es el default recomendado para no multiplicar los timeouts del modelo local.
- Si `qwen2.5:14b` corre en CPU, `build-graph` y la configuracion de eventos pueden caer a fallback determinista.
- Para smoke tests locales, `prepare --no-llm-profiles` es la ruta mas fiable.
