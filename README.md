# 🛸 drone-ops-planner

**Demo de planificación y trazabilidad de operativos con drones**, basada en la lógica de mi proyecto de título en Ingeniería Civil Industrial (PUCV).

> ⚠️ **Nota:** el sistema real fue desarrollado junto a mi equipo para la Dirección de Seguridad Pública de la Municipalidad de Viña del Mar y es propiedad de la institución. Este repositorio **no contiene su código ni sus datos**. Es una versión propia y simplificada, con **datos simulados**, para mostrar la lógica de asignación y los indicadores.

## Contexto real (proyecto de título)
- Sistema de planificación y trazabilidad operativa para el uso de drones, **implementado y en uso** en la institución.
- Definí la **lógica de asignación de recursos** y los **indicadores de eficiencia operativa**.
- Resultado: **−20% en el tiempo de coordinación** de operativos.

## Qué hace esta demo
1. Genera solicitudes de operativos simuladas (emergencia, fiscalización, evento, patrullaje).
2. Las despacha con dos políticas:
   - **Manual (FIFO):** orden de llegada y primer dron libre.
   - **Sistema:** prioridad por tipo de operativo + dron que termina antes (considera autonomía de batería y cambios de batería).
3. Calcula KPIs y exporta un **log de trazabilidad** (`trazabilidad_operativos.csv`): quién voló, con qué dron, cuándo y cuánto esperó cada operativo.

## Ejecutar
```bash
pip install -r requirements.txt
python drone_ops_planner.py --requests 35 --seed 7
```

## Resultado de ejemplo (simulado, seed 7)
| KPI | Manual (FIFO) | Sistema | Variación |
|---|---:|---:|---:|
| Coordinación promedio (min) | 14,6 | 11,4 | −21,9% |
| Espera promedio de emergencias (min) | 113,5 | 45,8 | −59,6% |
| Cambios de batería | 13 | 12 | −7,7% |

*Los parámetros de la simulación son supuestos y no replican datos reales.*

## Conceptos aplicados
Investigación de operaciones · despacho por prioridad · simulación de eventos discretos · diseño de KPIs · trazabilidad · Python (pandas, NumPy)

---
Autor: **Liam Esquivel González** · [LinkedIn](https://www.linkedin.com/in/liamesquivelg)
