"""Construcción y resolución de calendarios doble Round-Robin para la Premier League.

El CSV histórico aporta los equipos, no fija los partidos ni las jornadas del
nuevo calendario. El modelo asigna los partidos local/visitante a cada jornada,
minimiza breaks y permite activar restricciones operativas con datos adicionales.
"""

from __future__ import annotations

from itertools import combinations

import gurobipy as gp
import pandas as pd
from gurobipy import GRB


COLUMNAS_REQUERIDAS = {"HomeTeam", "AwayTeam"}


def _normalizar_pares(pares, equipos, nombre):
    """Valida y normaliza parejas no ordenadas de equipos."""
    resultado = []
    vistos = set()
    for par in pares or []:
        if isinstance(par, str) or len(par) != 2:
            raise ValueError(f"Cada elemento de {nombre} debe contener dos equipos: {par}")
        equipo_a, equipo_b = par
        if equipo_a not in equipos or equipo_b not in equipos or equipo_a == equipo_b:
            raise ValueError(f"Pareja inválida en {nombre}: {par}")
        clave = frozenset((equipo_a, equipo_b))
        if clave in vistos:
            raise ValueError(f"Pareja duplicada en {nombre}: {par}")
        vistos.add(clave)
        resultado.append(tuple(sorted((equipo_a, equipo_b))))
    return resultado


def resolver_instancia(
    temporada,
    url_csv,
    *,
    clasicos=None,
    estadios_compartidos=None,
    equipos_europeos=None,
    jornadas_criticas=None,
    max_clasicos_por_jornada=1,
    peso_breaks=1.0,
    peso_viajes=1.0,
    tiempo_limite=3600,
    desactivar_cortes_heuristicas=False,
    numero_equipos_esperado=20,
    mostrar_log=True,
):
    """Construye, resuelve y resume una instancia de temporada.

    El CSV se usa para obtener la lista de equipos y validar la temporada. El
    calendario optimizado es nuevo: el archivo no aporta números de jornada
    oficiales suficientes para fijar las fechas de los partidos históricos.

    El modelo crea variables de asignación partido-jornada, localía, breaks y
    viajes aproximados en jornadas críticas. Después agrega restricciones de
    Round-Robin, balance de localías y opciones operativas, minimiza la suma
    ponderada de breaks y viajes, y devuelve el estado y el calendario factible.
    La parte de viajes solo distingue localía/visita; no calcula distancias.
    """
    # Paso 1: descargar y validar la base de datos de la temporada.
    try:
        partidos_historicos = pd.read_csv(url_csv, encoding="latin-1")
    except Exception as error:
        raise RuntimeError(
            f"No se pudo leer la base de datos de {temporada} desde {url_csv}"
        ) from error

    faltantes = COLUMNAS_REQUERIDAS - set(partidos_historicos.columns)
    if faltantes:
        raise ValueError(f"El CSV de {temporada} no incluye las columnas: {sorted(faltantes)}")

    partidos_historicos = partidos_historicos.dropna(subset=["HomeTeam", "AwayTeam"]).copy()
    equipos = sorted(
        set(partidos_historicos["HomeTeam"].astype(str))
        | set(partidos_historicos["AwayTeam"].astype(str))
    )
    if len(equipos) != numero_equipos_esperado:
        raise ValueError(
            f"La temporada {temporada} contiene {len(equipos)} equipos; "
            f"se esperaban {numero_equipos_esperado}."
        )
    if len(equipos) < 2 or len(equipos) % 2 != 0:
        raise ValueError("El doble Round-Robin requiere un número par de equipos.")

    jornadas = list(range(1, 2 * (len(equipos) - 1) + 1))
    jornadas_break = jornadas[1:]
    clasicos = _normalizar_pares(clasicos, equipos, "clasicos")
    estadios_compartidos = _normalizar_pares(
        estadios_compartidos, equipos, "estadios_compartidos"
    )
    equipos_europeos = sorted(set(equipos_europeos or []))
    jornadas_criticas = sorted(set(jornadas_criticas or []))

    if not set(equipos_europeos).issubset(equipos):
        raise ValueError("Todos los equipos_europeos deben pertenecer a la temporada.")
    if not set(jornadas_criticas).issubset(jornadas):
        raise ValueError("Las jornadas_criticas deben pertenecer al horizonte del modelo.")
    if not isinstance(max_clasicos_por_jornada, int) or max_clasicos_por_jornada < 0:
        raise ValueError("max_clasicos_por_jornada debe ser un entero no negativo.")
    if peso_breaks < 0 or peso_viajes < 0:
        raise ValueError("Los pesos de la función objetivo deben ser no negativos.")
    if tiempo_limite <= 0:
        raise ValueError("tiempo_limite debe ser positivo.")

    # Paso 2: crear variables de partidos, localía, breaks y viajes.
    mdl = gp.Model(f"Calendario_Premier_League_{temporada}")
    if desactivar_cortes_heuristicas:
        mdl.setParam(GRB.Param.Cuts, 0)
        mdl.setParam(GRB.Param.Heuristics, 0)
    mdl.setParam("TimeLimit", tiempo_limite)
    modelo = mdl
    modelo.Params.OutputFlag = int(mostrar_log)

    x = modelo.addVars(
        [
            (local, visitante, jornada)
            for local in equipos
            for visitante in equipos
            if local != visitante
            for jornada in jornadas
        ],
        vtype=GRB.BINARY,
        name="x",
    )
    y = modelo.addVars(
        [(equipo, jornada) for equipo in equipos for jornada in jornadas],
        vtype=GRB.BINARY,
        name="y",
    )
    b_local = modelo.addVars(
        [(equipo, jornada) for equipo in equipos for jornada in jornadas_break],
        lb=0,
        vtype=GRB.CONTINUOUS,
        name="break_local",
    )
    b_visita = modelo.addVars(
        [(equipo, jornada) for equipo in equipos for jornada in jornadas_break],
        lb=0,
        vtype=GRB.CONTINUOUS,
        name="break_visita",
    )
    v = modelo.addVars(
        [
            (equipo, jornada)
            for equipo in equipos_europeos
            for jornada in jornadas_criticas
        ],
        lb=0,
        vtype=GRB.CONTINUOUS,
        name="fatiga_viaje",
    )

    # Paso 3: asegurar un partido por club/jornada y un localía por pareja.
    modelo.addConstrs(
        (
            gp.quicksum(
                x[equipo, rival, jornada] + x[rival, equipo, jornada]
                for rival in equipos
                if rival != equipo
            )
            == 1
            for equipo in equipos
            for jornada in jornadas
        ),
        name="un_partido_por_equipo_y_jornada",
    )
    modelo.addConstrs(
        (
            y[equipo, jornada]
            == gp.quicksum(
                x[equipo, rival, jornada] for rival in equipos if rival != equipo
            )
            for equipo in equipos
            for jornada in jornadas
        ),
        name="definicion_localia",
    )
    modelo.addConstrs(
        (
            gp.quicksum(x[local, visitante, jornada] for jornada in jornadas) == 1
            for local in equipos
            for visitante in equipos
            if local != visitante
        ),
        name="doble_round_robin",
    )
    modelo.addConstrs(
        (
            gp.quicksum(y[equipo, jornada] for jornada in jornadas)
            == len(jornadas) // 2
            for equipo in equipos
        ),
        name="balance_localia",
    )

    # Paso 4: definir exactamente breaks de local y de visita.
    modelo.addConstrs(
        (
            b_local[equipo, jornada]
            >= y[equipo, jornada - 1] + y[equipo, jornada] - 1
            for equipo in equipos
            for jornada in jornadas_break
        ),
        name="break_local_minimo",
    )
    modelo.addConstrs(
        (
            b_local[equipo, jornada] <= y[equipo, jornada - 1]
            for equipo in equipos
            for jornada in jornadas_break
        ),
        name="break_local_cota_anterior",
    )
    modelo.addConstrs(
        (
            b_local[equipo, jornada] <= y[equipo, jornada]
            for equipo in equipos
            for jornada in jornadas_break
        ),
        name="break_local_cota_actual",
    )
    modelo.addConstrs(
        (
            b_visita[equipo, jornada]
            >= 1 - y[equipo, jornada - 1] - y[equipo, jornada]
            for equipo in equipos
            for jornada in jornadas_break
        ),
        name="break_visita_minimo",
    )
    modelo.addConstrs(
        (
            b_visita[equipo, jornada] <= 1 - y[equipo, jornada - 1]
            for equipo in equipos
            for jornada in jornadas_break
        ),
        name="break_visita_cota_anterior",
    )
    modelo.addConstrs(
        (
            b_visita[equipo, jornada] <= 1 - y[equipo, jornada]
            for equipo in equipos
            for jornada in jornadas_break
        ),
        name="break_visita_cota_actual",
    )

    # Paso 5: incorporar límites operativos configurables del torneo.
    modelo.addConstrs(
        (
            y[equipo, jornada - 1]
            + y[equipo, jornada]
            + y[equipo, jornada + 1]
            <= 2
            for equipo in equipos
            for jornada in jornadas[1:-1]
        ),
        name="maximo_dos_localias_consecutivas",
    )
    modelo.addConstrs(
        (
            x[equipo_a, equipo_b, jornada] + x[equipo_b, equipo_a, jornada]
            <= max_clasicos_por_jornada
            for equipo_a, equipo_b in clasicos
            for jornada in jornadas
        ),
        name="limite_clasicos_simultaneos",
    )
    modelo.addConstrs(
        (
            y[equipo_a, jornada] + y[equipo_b, jornada] <= 1
            for equipo_a, equipo_b in estadios_compartidos
            for jornada in jornadas
        ),
        name="estadios_compartidos",
    )
    modelo.addConstrs(
        (
            v[equipo, jornada] == 1 - y[equipo, jornada]
            for equipo in equipos_europeos
            for jornada in jornadas_criticas
        ),
        name="fatiga_por_viaje",
    )

    # Paso 6: minimizar breaks y desplazamientos en fechas críticas.
    modelo.setObjective(
        peso_breaks
        * gp.quicksum(
            b_local[equipo, jornada] + b_visita[equipo, jornada]
            for equipo in equipos
            for jornada in jornadas_break
        )
        + peso_viajes
        * gp.quicksum(
            v[equipo, jornada]
            for equipo in equipos_europeos
            for jornada in jornadas_criticas
        ),
        GRB.MINIMIZE,
    )

    modelo.update()
    if mostrar_log:
        print(
            f"{temporada}: {len(equipos)} equipos, {len(jornadas)} jornadas, "
            f"{modelo.NumVars:,} variables y {modelo.NumConstrs:,} restricciones."
        )

    # Paso 7: resolver y extraer el calendario si existe una solución factible.
    modelo.optimize()
    calendario = pd.DataFrame(columns=["Jornada", "Local", "Visitante"])
    breaks = None
    viajes_criticos = None
    objetivo = None
    if modelo.SolCount > 0:
        encuentros = [
            (jornada, local, visitante)
            for local in equipos
            for visitante in equipos
            if local != visitante
            for jornada in jornadas
            if x[local, visitante, jornada].X > 0.5
        ]
        calendario = pd.DataFrame(
            encuentros, columns=["Jornada", "Local", "Visitante"]
        ).sort_values(["Jornada", "Local"]).reset_index(drop=True)
        breaks = sum(variable.X for variable in b_local.values()) + sum(
            variable.X for variable in b_visita.values()
        )
        viajes_criticos = sum(variable.X for variable in v.values())
        objetivo = modelo.ObjVal

    return {
        "temporada": temporada,
        "url_csv": url_csv,
        "partidos_historicos": partidos_historicos,
        "equipos": equipos,
        "modelo": modelo,
        "estado": modelo.Status,
        "soluciones_factibles": modelo.SolCount,
        "objetivo": objetivo,
        "cota": modelo.ObjBoundC,
        "gap": modelo.MIPGap if modelo.SolCount > 0 else None,
        "tiempo": modelo.Runtime,
        "nodos": modelo.NodeCount,
        "breaks": breaks,
        "viajes_criticos": viajes_criticos,
        "calendario": calendario,
    }
