# Integration Notebook Checklist

Objetivo: validar la libreria `eu_ai_act` desde el notebook sin depender de un entrenamiento largo/inestable.

## Precondiciones

- Entorno sincronizado: `uv sync`
- Tests en verde: `uv run pytest -q`
- Pesos disponibles en alguno de estos paths:
  - `case/xray_class.weights.h5`
  - `xray_class.weights.h5`

## Pasos de validacion

1. Abrir `case/train-simple-xray-cnn.ipynb`.
2. Confirmar que `RUN_TRAINING=False` (por defecto).
3. Ejecutar celdas de preparacion de datos y modelo.
4. Ejecutar celdas de integracion real con `eu_ai_act`.
5. Verificar salida final de integracion:
   - `outputs/real_integration_test/assessment.json`
   - `outputs/real_integration_test/assessment.md`
   - `outputs/real_integration_test/assessment.pdf`

## Criterio de exito

- El flujo termina sin exigir reentrenamiento.
- Se generan los tres artefactos de reporte.
- La salida imprime `Integration test completed`.
