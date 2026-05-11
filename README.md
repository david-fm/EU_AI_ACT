## EU AI ACT - Compliance Evaluator para Vision Artificial

Repositorio orientado a evaluacion de cumplimiento para modelos de vision (Keras/TensorFlow/PyTorch) con foco en:

- registro de riesgos (risk register),
- analisis FMEA simplificado,
- fairness por subgrupos,
- stress testing de robustez,
- export de resultados en JSON, Markdown y PDF.

## Estado actual del proyecto

- Base tecnica funcional: CLI + pipeline de evaluacion + exportes.
- Integracion validada: carpeta de ejemplo con resultado real en outputs/real_integration_test.
- Calidad base estable: tests automatizados pasando.
- Pendiente: evolucionar desde evaluador SDK hacia plataforma completa de cumplimiento (backlog extendido).

## Ejecucion rapida

Requisitos:

- Python 3.12+
- uv

Instalacion:

```bash
uv sync
```

Ejecutar tests:

```bash
uv run pytest -q
```

Ejecutar una evaluacion:

```bash
uv run eu-ai-act \
	--framework keras \
	--model-path case/xray_class.weights.h5 \
	--input path/al/dataset.json \
	--output-dir outputs/run_01
```

## Estructura principal

- src/eu_ai_act/adapters: adaptadores de frameworks y carga de modelos.
- src/eu_ai_act/compliance: primitivas de riesgo, fairness, FMEA, stress y taxonomia.
- src/eu_ai_act/evaluation: pipeline de evaluacion.
- src/eu_ai_act/reporting: exportadores de artefactos.
- tests: suite de pruebas de adaptadores, datos y evaluacion.

## Organizacion recomendada

Para ejecutar el trabajo de forma ordenada, seguir el tablero en:

- EXECUTION_BOARD.md

Ese documento separa claramente:

1. Lo que ya existe y se debe consolidar.
2. Lo que falta para llegar al plan completo.
3. El orden de implementacion por bloques cortos y verificables.
