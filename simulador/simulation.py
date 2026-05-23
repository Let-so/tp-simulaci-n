import math
import random
from dataclasses import dataclass, field
from typing import Optional

# ─── Constants ───────────────────────────────────────────────────────────────
OPEN_TIME = 0        # 08:00 → minute 0
CLOSE_TIME = 480     # 16:00 → minute 480
INF = float('inf')

ESTADO_LIBRE      = "Libre"
ESTADO_OCUPADO    = "Ocupado"
ESTADO_BLOQUEADA  = "Bloqueada"

EVT_LLEGADA_AUTO    = "Llegada Auto"
EVT_LLEGADA_CAMION  = "Llegada Camioneta"
EVT_FIN_FRENO_1     = "Fin Frenos L1"
EVT_FIN_FRENO_2     = "Fin Frenos L2"
EVT_FIN_LUCES_1     = "Fin Luces L1"
EVT_FIN_LUCES_2     = "Fin Luces L2"
EVT_FIN_SIM         = "Fin Simulación"

# ─── Random generators ───────────────────────────────────────────────────────

def next_auto(rnd=None):
    if rnd is None:
        rnd = random.random()
    val = -15 * math.log(1 - rnd)
    return rnd, round(val, 4)

def next_camion(rnd=None):
    if rnd is None:
        rnd = random.random()
    val = -30 * math.log(1 - rnd)
    return rnd, round(val, 4)

def tiempo_freno(rnd=None):
    if rnd is None:
        rnd = random.random()
    val = 4 + rnd * (7 - 4)
    return rnd, round(val, 4)

def tiempo_luces(rnd=None):
    if rnd is None:
        rnd = random.random()
    val = 6 + rnd * (10 - 6)
    return rnd, round(val, 4)

# ─── Data structures ─────────────────────────────────────────────────────────

@dataclass
class Vehiculo:
    id: int
    tipo: str          # "Auto" | "Camioneta"
    hora_llegada: float
    hora_inicio_espera: float = 0.0
    hora_fin_espera: float = 0.0

@dataclass
class EstacionFreno:
    id: int
    estado: str = ESTADO_LIBRE
    vehiculo_id: Optional[int] = None
    fin_atencion: float = INF

@dataclass
class EstacionLuces:
    id: int
    estado: str = ESTADO_LIBRE
    vehiculo_id: Optional[int] = None
    fin_atencion: float = INF

# ─── Main simulation ─────────────────────────────────────────────────────────

def run_simulation(tiempo_max: int, inicio_mostrar: float, cant_mostrar: int):
    """
    Runs the RTV simulation.
    Returns (rows, stats) where rows is a list of state-vector dicts.
    """
    rng = random.Random()

    # State
    frenos  = [EstacionFreno(1),  EstacionFreno(2)]
    luces   = [EstacionLuces(1), EstacionLuces(2)]

    cola_autos: list[Vehiculo]    = []
    cola_camiones: list[Vehiculo] = []

    # Next-event times
    rnd_la, dt_auto   = next_auto()
    rnd_lc, dt_camion = next_camion()
    t_llegada_auto   = dt_auto
    t_llegada_camion = dt_camion

    # Counters & accumulators
    vehiculo_counter = 0
    autos_atendidos   = 0
    camiones_atendidos = 0
    suma_espera_autos   = 0.0
    suma_espera_camiones = 0.0
    tiempo_bloqueada_f1 = 0.0
    tiempo_bloqueada_f2 = 0.0
    t_inicio_bloqueo_f1 = None
    t_inicio_bloqueo_f2 = None
    hora_fin_jornada = tiempo_max

    t = 0.0
    iter_count = 0
    cerrado = False   # once True, no new arrivals

    rows = []   # state-vector rows to display

    # Track pending rnds used in current event step
    pending_rnds: dict = {}

    def min_event():
        candidates = []
        if not cerrado:
            candidates.append((t_llegada_auto,   EVT_LLEGADA_AUTO))
            candidates.append((t_llegada_camion,  EVT_LLEGADA_CAMION))
        for f in frenos:
            if f.estado != ESTADO_LIBRE:
                candidates.append((f.fin_atencion, f"Fin Frenos L{f.id}"))
        for l in luces:
            if l.estado != ESTADO_LIBRE:
                candidates.append((l.fin_atencion, f"Fin Luces L{l.id}"))
        if not candidates:
            return INF, EVT_FIN_SIM
        return min(candidates, key=lambda x: x[0])

    def proximos_eventos():
        evts = []
        if not cerrado:
            evts.append(f"{EVT_LLEGADA_AUTO}@{t_llegada_auto:.2f}")
            evts.append(f"{EVT_LLEGADA_CAMION}@{t_llegada_camion:.2f}")
        for f in frenos:
            if f.fin_atencion < INF:
                evts.append(f"Fin Frenos L{f.id}@{f.fin_atencion:.2f}")
        for l in luces:
            if l.fin_atencion < INF:
                evts.append(f"Fin Luces L{l.id}@{l.fin_atencion:.2f}")
        return " | ".join(evts) if evts else "—"

    def snapshot(evento, rnds_usados):
        return {
            "iter": iter_count,
            "hora": round(t, 4),
            "evento": evento,
            "proximos": proximos_eventos(),
            # frenos
            "f1_estado": frenos[0].estado,
            "f1_vid":    frenos[0].vehiculo_id,
            "f1_fin":    round(frenos[0].fin_atencion, 4) if frenos[0].fin_atencion < INF else "—",
            "f2_estado": frenos[1].estado,
            "f2_vid":    frenos[1].vehiculo_id,
            "f2_fin":    round(frenos[1].fin_atencion, 4) if frenos[1].fin_atencion < INF else "—",
            # luces
            "l1_estado": luces[0].estado,
            "l1_vid":    luces[0].vehiculo_id,
            "l1_fin":    round(luces[0].fin_atencion, 4) if luces[0].fin_atencion < INF else "—",
            "l2_estado": luces[1].estado,
            "l2_vid":    luces[1].vehiculo_id,
            "l2_fin":    round(luces[1].fin_atencion, 4) if luces[1].fin_atencion < INF else "—",
            # colas
            "cola_autos":    len(cola_autos),
            "cola_camiones": len(cola_camiones),
            # acumuladores
            "autos_atend":    autos_atendidos,
            "camiones_atend": camiones_atendidos,
            "prom_esp_autos":    round(suma_espera_autos   / autos_atendidos,    4) if autos_atendidos    else 0,
            "prom_esp_camiones": round(suma_espera_camiones / camiones_atendidos, 4) if camiones_atendidos else 0,
            "t_bloq_f1": round(tiempo_bloqueada_f1, 4),
            "t_bloq_f2": round(tiempo_bloqueada_f2, 4),
            "pct_bloq":  round((tiempo_bloqueada_f1 + tiempo_bloqueada_f2) / (2 * max(t, 1)) * 100, 2),
            # rnds
            "rnds": dict(rnds_usados),
        }

    def intentar_siguiente_vehiculo(linea_idx):
        """Try to assign next queued vehicle to freno[linea_idx] if free."""
        f = frenos[linea_idx]
        if f.estado != ESTADO_LIBRE:
            return
        # priority: camiones first
        if cola_camiones:
            v = cola_camiones.pop(0)
        elif cola_autos:
            v = cola_autos.pop(0)
        else:
            return
        v.hora_fin_espera = t
        espera = t - v.hora_inicio_espera
        if v.tipo == "Auto":
            nonlocal suma_espera_autos, autos_atendidos
            suma_espera_autos += espera
            autos_atendidos   += 1
        else:
            nonlocal suma_espera_camiones, camiones_atendidos
            suma_espera_camiones += espera
            camiones_atendidos   += 1
        r, dur = tiempo_freno()
        pending_rnds[f"rnd_freno_L{linea_idx+1}"] = round(r, 6)
        f.estado      = ESTADO_OCUPADO
        f.vehiculo_id = v.id
        f.fin_atencion = t + dur

    # ─── Event loop ──────────────────────────────────────────────────────────
    while iter_count < 100000:
        t_next, evt_name = min_event()
        if t_next == INF:
            break

        # Check if we've reached end of simulation
        if t_next > tiempo_max and cerrado:
            # check if any vehicle still in system
            any_active = any(f.estado != ESTADO_LIBRE for f in frenos) or \
                         any(l.estado != ESTADO_LIBRE for l in luces) or \
                         cola_autos or cola_camiones
            if not any_active:
                break

        t = t_next
        iter_count += 1
        pending_rnds = {}

        # Mark closed if past CLOSE_TIME
        if t >= CLOSE_TIME and not cerrado:
            cerrado = True

        # ── Llegada Auto ──────────────────────────────────────────────────
        if evt_name == EVT_LLEGADA_AUTO and not cerrado:
            vehiculo_counter += 1
            v = Vehiculo(vehiculo_counter, "Auto", t)
            v.hora_inicio_espera = t
            # schedule next arrival
            rnd_la, dt = next_auto()
            pending_rnds["rnd_llegada_auto"] = round(rnd_la, 6)
            t_llegada_auto = t + dt

            # find free freno (prefer line with shorter queue, simple: first free)
            asignado = False
            for idx in range(2):
                if frenos[idx].estado == ESTADO_LIBRE:
                    r, dur = tiempo_freno()
                    pending_rnds[f"rnd_freno_L{idx+1}"] = round(r, 6)
                    frenos[idx].estado       = ESTADO_OCUPADO
                    frenos[idx].vehiculo_id  = v.id
                    frenos[idx].fin_atencion = t + dur
                    suma_espera_autos += 0
                    autos_atendidos   += 1
                    asignado = True
                    break
            if not asignado:
                cola_autos.append(v)

        # ── Llegada Camioneta ─────────────────────────────────────────────
        elif evt_name == EVT_LLEGADA_CAMION and not cerrado:
            vehiculo_counter += 1
            v = Vehiculo(vehiculo_counter, "Camioneta", t)
            v.hora_inicio_espera = t
            rnd_lc, dt = next_camion()
            pending_rnds["rnd_llegada_camion"] = round(rnd_lc, 6)
            t_llegada_camion = t + dt

            asignado = False
            for idx in range(2):
                if frenos[idx].estado == ESTADO_LIBRE:
                    r, dur = tiempo_freno()
                    pending_rnds[f"rnd_freno_L{idx+1}"] = round(r, 6)
                    frenos[idx].estado       = ESTADO_OCUPADO
                    frenos[idx].vehiculo_id  = v.id
                    frenos[idx].fin_atencion = t + dur
                    suma_espera_camiones += 0
                    camiones_atendidos   += 1
                    asignado = True
                    break
            if not asignado:
                cola_camiones.append(v)

        # ── Fin Frenos ────────────────────────────────────────────────────
        elif evt_name in (EVT_FIN_FRENO_1, EVT_FIN_FRENO_2):
            idx = 0 if evt_name == EVT_FIN_FRENO_1 else 1
            f = frenos[idx]
            l = luces[idx]
            vid = f.vehiculo_id

            if l.estado == ESTADO_LIBRE:
                # advance to luces
                r, dur = tiempo_luces()
                pending_rnds[f"rnd_luces_L{idx+1}"] = round(r, 6)
                l.estado       = ESTADO_OCUPADO
                l.vehiculo_id  = vid
                l.fin_atencion = t + dur
                f.estado       = ESTADO_LIBRE
                f.vehiculo_id  = None
                f.fin_atencion = INF
                # try to bring next vehicle in
                intentar_siguiente_vehiculo(idx)
            else:
                # BLOCK: vehicle stays, freno blocked
                f.estado = ESTADO_BLOQUEADA
                f.fin_atencion = INF
                if idx == 0:
                    t_inicio_bloqueo_f1 = t
                else:
                    t_inicio_bloqueo_f2 = t

        # ── Fin Luces ─────────────────────────────────────────────────────
        elif evt_name in (EVT_FIN_LUCES_1, EVT_FIN_LUCES_2):
            idx = 0 if evt_name == EVT_FIN_LUCES_1 else 1
            l = luces[idx]
            f = frenos[idx]

            # vehicle leaves system
            if t > CLOSE_TIME:
                hora_fin_jornada = t

            l.estado       = ESTADO_LIBRE
            l.vehiculo_id  = None
            l.fin_atencion = INF

            # if freno was blocked, unblock it → now this vehicle goes to luces
            if f.estado == ESTADO_BLOQUEADA:
                # accumulate block time
                if idx == 0 and t_inicio_bloqueo_f1 is not None:
                    tiempo_bloqueada_f1 += t - t_inicio_bloqueo_f1
                    t_inicio_bloqueo_f1 = None
                elif idx == 1 and t_inicio_bloqueo_f2 is not None:
                    tiempo_bloqueada_f2 += t - t_inicio_bloqueo_f2
                    t_inicio_bloqueo_f2 = None

                vid_bloq = f.vehiculo_id
                r, dur = tiempo_luces()
                pending_rnds[f"rnd_luces_L{idx+1}"] = round(r, 6)
                l.estado       = ESTADO_OCUPADO
                l.vehiculo_id  = vid_bloq
                l.fin_atencion = t + dur
                f.estado       = ESTADO_LIBRE
                f.vehiculo_id  = None
                f.fin_atencion = INF
                # bring next in queue
                intentar_siguiente_vehiculo(idx)
            else:
                # freno was free (or occupied by someone else, shouldn't happen)
                pass

        # ── Build row ─────────────────────────────────────────────────────
        row = snapshot(evt_name, pending_rnds)
        rows.append(row)

    # ── Final stats ───────────────────────────────────────────────────────
    stats = {
        "prom_esp_autos":    round(suma_espera_autos    / autos_atendidos,    4) if autos_atendidos    else 0,
        "prom_esp_camiones": round(suma_espera_camiones / camiones_atendidos, 4) if camiones_atendidos else 0,
        "pct_bloq_f1":       round(tiempo_bloqueada_f1 / max(t, 1) * 100, 2),
        "pct_bloq_f2":       round(tiempo_bloqueada_f2 / max(t, 1) * 100, 2),
        "pct_bloq_total":    round((tiempo_bloqueada_f1 + tiempo_bloqueada_f2) / (2 * max(t, 1)) * 100, 2),
        "hora_fin_jornada":  round(hora_fin_jornada, 2),
        "total_autos":       autos_atendidos,
        "total_camiones":    camiones_atendidos,
        "total_iter":        iter_count,
    }

    # Filter rows to show
    display_rows = [r for r in rows if r["hora"] >= inicio_mostrar][:cant_mostrar]
    last_row = rows[-1] if rows else None

    return display_rows, last_row, stats, rows
