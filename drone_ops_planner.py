"""
drone-ops-planner
-----------------
Demo de planificacion y trazabilidad de operativos con drones.

Inspirado en mi proyecto de titulo (PUCV) para la Direccion de Seguridad
Publica de una municipalidad. Este repositorio NO contiene codigo ni datos
de la institucion: todo se genera con datos simulados para mostrar la logica.

Que hace:
  1. Genera solicitudes de operativos (emergencia, fiscalizacion, evento, patrullaje).
  2. Asigna drones y pilotos segun prioridad, autonomia de bateria y turnos.
  3. Compara contra una asignacion "manual" (orden de llegada, FIFO).
  4. Calcula KPIs y exporta un log de trazabilidad a CSV.

Uso:
  python drone_ops_planner.py --requests 35 --seed 7
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PRIORITY = {"emergencia": 1, "fiscalizacion": 2, "evento": 3, "patrullaje": 4}
DURATION_MIN = {"emergencia": (20, 45), "fiscalizacion": (30, 60),
                "evento": (60, 120), "patrullaje": (40, 90)}
SHIFT_START, SHIFT_END = 8 * 60, 20 * 60          # turno 08:00 - 20:00 (minutos)
SETUP_MIN = 10                                    # traslado + preparacion
MANUAL_COORD_MIN = (10, 19)                       # coordinacion por telefono/radio
SYSTEM_COORD_MIN = (8, 15)                        # coordinacion con el sistema


@dataclass
class Drone:
    drone_id: str
    battery_min: int                  # autonomia por vuelo
    available_at: int = SHIFT_START
    flights: int = 0


@dataclass
class Pilot:
    pilot_id: str
    available_at: int = SHIFT_START
    minutes_flown: int = 0
    log: list = field(default_factory=list)


def generate_requests(n: int, rng: np.random.Generator) -> pd.DataFrame:
    types = rng.choice(list(PRIORITY), size=n, p=[0.15, 0.30, 0.15, 0.40])
    arrival = np.sort(rng.integers(SHIFT_START, SHIFT_END - 120, size=n))
    duration = [int(rng.integers(*DURATION_MIN[t])) for t in types]
    return pd.DataFrame({
        "request_id": [f"OP-{i:03d}" for i in range(1, n + 1)],
        "type": types,
        "priority": [PRIORITY[t] for t in types],
        "arrival_min": arrival,
        "duration_min": duration,
        "sector": rng.choice(["Norte", "Centro", "Sur", "Costa"], size=n),
    })


def build_fleet() -> tuple[list[Drone], list[Pilot]]:
    drones = [Drone("DR-01", 45), Drone("DR-02", 45), Drone("DR-03", 90), Drone("DR-04", 120)]
    pilots = [Pilot("PI-A"), Pilot("PI-B"), Pilot("PI-C"), Pilot("PI-D")]
    return drones, pilots


def plan(requests: pd.DataFrame, mode: str, rng: np.random.Generator) -> pd.DataFrame:
    """mode='manual' -> FIFO y primer dron libre; mode='system' -> prioridad + mejor ajuste."""
    drones, pilots = build_fleet()
    coord_range = MANUAL_COORD_MIN if mode == "manual" else SYSTEM_COORD_MIN
    pending = requests.copy()
    pending["coordination_min"] = rng.integers(*coord_range, size=len(pending))
    pending["ready_min"] = pending.arrival_min + pending.coordination_min
    rows = []
    while len(pending):
        # despacho por eventos: cuando se libera un piloto, se elige entre
        # las solicitudes ya coordinadas (listas) en ese momento
        pilot = min(pilots, key=lambda p: (p.available_at, p.minutes_flown))
        t = max(pilot.available_at, pending.ready_min.min())
        ready = pending[pending.ready_min <= t]
        key = ["ready_min"] if mode == "manual" else ["priority", "ready_min"]
        r = ready.sort_values(key).iloc[0]
        pending = pending.drop(r.name)
        if mode == "manual":
            drone = min(drones, key=lambda d: d.available_at)
        else:
            # mejor ajuste: dron que termina antes el operativo (considera espera
            # y cambios de bateria); desempate por menor autonomia para reservar
            # los drones de mayor autonomia a los vuelos largos
            def finish(d: Drone) -> int:
                swaps = int(np.ceil(r.duration_min / d.battery_min)) - 1
                return max(d.available_at, t) + r.duration_min + 15 * swaps
            drone = min(drones, key=lambda d: (finish(d), d.battery_min))
        coord = int(r.coordination_min)
        start = max(t, drone.available_at) + SETUP_MIN
        # si la bateria no alcanza se requiere un cambio de bateria (+15 min)
        battery_swaps = int(np.ceil(r.duration_min / drone.battery_min)) - 1
        end = start + r.duration_min + 15 * battery_swaps
        drone.available_at, pilot.available_at = end, end
        drone.flights += 1
        pilot.minutes_flown += r.duration_min
        rows.append({**r.to_dict(), "mode": mode, "drone_id": drone.drone_id,
                     "pilot_id": pilot.pilot_id, "coordination_min": coord,
                     "start_min": start, "end_min": end,
                     "wait_min": start - r.arrival_min, "battery_swaps": battery_swaps,
                     "within_shift": end <= SHIFT_END})
    return pd.DataFrame(rows)


def kpis(df: pd.DataFrame) -> pd.Series:
    urgent = df[df.priority == 1]
    return pd.Series({
        "operativos": len(df),
        "coordinacion_prom_min": df.coordination_min.mean(),
        "espera_prom_min": df.wait_min.mean(),
        "espera_emergencias_min": urgent.wait_min.mean() if len(urgent) else 0,
        "cambios_bateria": df.battery_swaps.sum(),
        "cumplimiento_turno_%": 100 * df.within_shift.mean(),
    }).round(1)


def fmt(minutes: int) -> str:
    return f"{int(minutes) // 60:02d}:{int(minutes) % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--requests", type=int, default=35)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="trazabilidad_operativos.csv")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    requests = generate_requests(args.requests, rng)
    manual = plan(requests, "manual", np.random.default_rng(args.seed))
    system = plan(requests, "system", np.random.default_rng(args.seed))

    table = pd.DataFrame({"manual (FIFO)": kpis(manual), "sistema": kpis(system)})
    table["variacion_%"] = (100 * (table["sistema"] / table["manual (FIFO)"] - 1)).round(1)
    print("\n=== KPIs de operacion (datos simulados) ===")
    print(table.to_string())

    log = system.sort_values("start_min").assign(
        llegada=lambda d: d.arrival_min.map(fmt),
        inicio=lambda d: d.start_min.map(fmt),
        termino=lambda d: d.end_min.map(fmt))
    cols = ["request_id", "type", "sector", "llegada", "inicio", "termino",
            "drone_id", "pilot_id", "wait_min", "battery_swaps"]
    log[cols].to_csv(args.out, index=False)
    print(f"\nLog de trazabilidad guardado en {args.out}")
    print(log[cols].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
