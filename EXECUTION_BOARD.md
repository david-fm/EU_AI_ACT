# Tablero de Ejecucion - EU_AI_ACT

## 1) Enfoque acordado

Secuencia de trabajo acordada:

1. Finiquitar limpieza del notebook de prueba y dejar estable la integracion real con la libreria.
2. Consolidacion tecnica: ampliar tests y reforzar uso correcto de fairlearn.
3. Ejecutar enriquecimiento funcional (Bloque 1).
4. Reorganizar estructura de archivos para integrarlo como modulo claro dentro del paquete (Bloque 3).
5. Dejar Bloque 4 aparcado para una fase posterior contigo.

## 2) Estado actual (14-04-2026)

- [x] CLI funcional para evaluaciones.
- [x] Exportes JSON/MD/PDF operativos.
- [x] Pipeline fairness + stress operativo.
- [x] Base de tests pasando en local.
- [x] Notebook ajustado para evitar degradacion por entrenamiento inestable (entrenamiento opcional + carga de pesos si existen).
- [x] Versionado de ejecuciones incorporado (`run_id`, `config_hash`, timestamp UTC).
- [x] Comparativa run actual vs run anterior incorporada en assessment y exportes.
- [x] Estructura modular interna iniciada (`eu_ai_act.core` y `eu_ai_act.operations`) sin romper imports publicos.
- [x] Checklist de validacion de notebook documentado en `docs/integration-notebook-checklist.md`.

## 3) Plan de ejecucion por bloques

### Bloque 0 - Cierre notebook + consolidacion base

Objetivo: asegurar que la prueba de notebook valida la libreria sin depender de entrenamiento largo/inestable.

Alcance:

- Fijar notebook con modo de entrenamiento opcional (por defecto desactivado).
- Cargar pesos guardados cuando existan para estabilizar predicciones.
- Mantener celda de integracion real contra `eu_ai_act` como paso obligatorio de validacion.
- Documentar comando y criterio de exito de la prueba real.

Criterios de terminado:

- Notebook ejecuta flujo de integracion y genera reportes en `outputs/real_integration_test`.
- No hay dependencia dura de re-entrenar para validar la libreria.

### Bloque Consolidacion - tests + fairlearn

Objetivo: reforzar calidad y trazabilidad tecnica antes de enriquecer funcionalidades.

Alcance:

- Aumentar cobertura de tests en `compliance/fairness.py` y `evaluation/pipeline.py`.
- Añadir tests de regresion de formatos de salida (`assessment.json`, `assessment.md`, `assessment.pdf`).
- Validar uso consistente de metricas fairlearn (equalized odds, disparate impact) por campo sensible.
- Incluir casos borde: grupos desbalanceados, metadatos ausentes y sin `y_true` completo.

Entregable:

- baseline de calidad endurecido para evolucionar sin regresiones.

### Bloque 1 - Enriquecimiento Riesgo/FMEA/Fairness

Objetivo: alinear la salida del paquete con `plan.md` en profundidad tecnica.

Alcance:

- FMEA enriquecido: causas, controles y acciones sugeridas.
- Umbrales de severidad/rpn con banderas automaticas.
- Riesgo residual y priorizacion de mitigaciones.
- Fairness extendido: metricas de calibracion, umbrales por grupo y resumen accionable.
- Taxonomias de stress por dominio mas robustas.

Entregable:

- `assessment` enriquecido y trazable para auditoria tecnica.

### Bloque 3 - Modularizacion interna del paquete

Objetivo: dejar la base preparada para escalar como plataforma sin romper APIs actuales.

Alcance:

- Reorganizar carpetas para separar claramente:
  - nucleo de evaluacion,
  - capa de cumplimiento/riesgo,
  - capa de integracion operativa.
- Mantener compatibilidad en imports publicos (`eu_ai_act.*`).
- Definir punto de entrada de modulo para ejecuciones periodicas y comparativas entre runs.

Entregable:

- estructura modular limpia, lista para siguiente fase.

### Bloque 4 - Aplazado (planificacion conjunta posterior)

Estado:

- No se ejecuta ahora.
- Se revisa contigo en una sesion especifica de arquitectura/alcance.

## 4) Backlog inmediato priorizado (estado tras ejecucion)

- [x] Añadir tests de regresion para exportes en `reporting/exporters.py`.
- [x] Añadir tests de borde para `evaluate_fairness_by_field`.
- [x] Añadir tests de riesgo residual y banderas de severidad en pipeline.
- [x] Crear `docs/integration-notebook-checklist.md` con pasos de validacion real.
- [x] Versionar ejecuciones de evaluacion (`run_id`, `config_hash`, timestamp).
- [x] Añadir comparativa `run_actual` vs `run_anterior` en reporte.
- [x] Definir y aplicar cobertura minima para codigo nuevo (objetivo: 80%).
- [x] Preparar propuesta de estructura modular para Bloque 3.

## 5) Cadencia de trabajo

- Lunes: seleccionar maximo 5 tareas activas.
- Diario: checkpoint de 15 minutos con bloqueos y siguiente accion.
- Viernes: demo, evidencia reproducible y cierre de tareas abiertas.

Reglas de ejecucion:

- No iniciar tareas nuevas con pendientes criticos del bloque activo.
- Cada tarea cierra con test automatizado o evidencia ejecutable.
- Priorizar estabilidad y trazabilidad sobre cantidad de features.

## 6) Definicion de terminado (DoD)

Una tarea se cierra solo si cumple todo:

- codigo mergeado,
- tests relevantes pasando,
- artefacto/documentacion actualizada,
- evidencia reproducible (comando + resultado esperado),
- impacto regulatorio anotado de forma breve.
