"""
Module : KPI — budget_optique.py
Role   : Calcul du budget optique d'une liaison OLT-ONT GPON
Entree : parametres de la liaison (distance, splitter, connecteurs)
Sortie : dict avec pertes detaillees et status

Formules :
    perte_fibre       = fiber_km * 0.35 dB/km
    perte_connecteurs = nb_connectors * 0.3 dB
    perte_splitter    = selon ratio (1:16=13dB, 1:32=16.5dB, ...)
    total_budget_dB   = perte_fibre + perte_connecteurs + perte_splitter

Status CDC :
    OK           si total_budget_dB <= 28 dB
    Risque       si total_budget_dB <= 32 dB
    Non conforme si total_budget_dB >  32 dB
"""
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO,
                    format="[budget_optique] %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── Constantes physiques GPON ──────────────────────────────────
ATT_FIBRE_DB_KM = 0.35   # attenuation fibre monomode (dB/km)
ATT_CONNECTOR   = 0.30   # perte par connecteur (dB)

# Pertes splitter selon ratio (dB) — valeurs standard ITU-T G.984
ATT_SPLITTER = {
    16 : 13.0,
    32 : 16.5,
    64 : 19.0,
    128: 22.0,
    256: 24.0,
}

# Seuils de status alignes sur le dataset encadrant
SEUIL_OK     = 28.0
SEUIL_RISQUE = 32.0


def compute_optical_budget(fiber_km: float,
                           split_ratio: int,
                           nb_connectors: int = 4) -> dict:
    """
    Calcule le budget optique d'une liaison OLT-ONT.

    Args:
        fiber_km      : longueur totale de fibre en km
        split_ratio   : ratio du splitter (16, 32, 64, 128, 256)
        nb_connectors : nombre de connecteurs (defaut 4)

    Returns:
        dict avec cles :
        fiber_km, split_ratio, connectors,
        fiber_loss_dB, connector_loss_dB, splitter_loss_dB,
        total_budget_dB, status
    """
    if split_ratio not in ATT_SPLITTER:
        raise ValueError(
            f"split_ratio {split_ratio} invalide. "
            f"Valeurs acceptees : {list(ATT_SPLITTER.keys())}"
        )

    # ── Calcul des pertes ──────────────────────────────────────
    fiber_loss_dB     = round(fiber_km * ATT_FIBRE_DB_KM, 2)
    connector_loss_dB = round(nb_connectors * ATT_CONNECTOR, 2)
    splitter_loss_dB  = ATT_SPLITTER[split_ratio]
    total_budget_dB   = round(
        fiber_loss_dB + connector_loss_dB + splitter_loss_dB, 2
    )

    # ── Status aligne sur dataset encadrant ───────────────────
    if total_budget_dB <= SEUIL_OK:
        status = "OK"
    elif total_budget_dB <= SEUIL_RISQUE:
        status = "Risque"
    else:
        status = "Non conforme"

    result = {
        "fiber_km"         : fiber_km,
        "split_ratio"      : f"1:{split_ratio}",
        "connectors"       : nb_connectors,
        "fiber_loss_dB"    : fiber_loss_dB,
        "connector_loss_dB": connector_loss_dB,
        "splitter_loss_dB" : splitter_loss_dB,
        "total_budget_dB"  : total_budget_dB,
        "status"           : status,
    }

    logger.info(
        f"Liaison {fiber_km}km 1:{split_ratio} "
        f"-> {total_budget_dB}dB [{status}]"
    )
    return result


def compute_all_scenarios(df_optical: pd.DataFrame) -> pd.DataFrame:
    """
    Applique compute_optical_budget sur tous les scenarios.
    Utilise splitter_loss_dB du DataFrame si presente.
    """
    results = []
    for _, row in df_optical.iterrows():
        ratio = int(str(row["split_ratio"]).replace("1:", ""))

        # Utiliser splitter_loss_dB du CSV si disponible
        if "splitter_loss_dB" in row.index:
            splitter_loss = float(row["splitter_loss_dB"])
        else:
            splitter_loss = ATT_SPLITTER.get(ratio, 16.5)

        fiber_loss_dB     = round(float(row["fiber_km"]) * ATT_FIBRE_DB_KM, 2)
        connector_loss_dB = round(int(row["connectors"]) * ATT_CONNECTOR, 2)
        total_budget_dB   = round(
            fiber_loss_dB + connector_loss_dB + splitter_loss, 2
        )

        if total_budget_dB <= SEUIL_OK:
            status = "OK"
        elif total_budget_dB <= SEUIL_RISQUE:
            status = "Risque"
        else:
            status = "Non conforme"

        results.append({
            "scenario"         : row["scenario"],
            "fiber_km"         : float(row["fiber_km"]),
            "connectors"       : int(row["connectors"]),
            "split_ratio"      : f"1:{ratio}",
            "fiber_loss_dB"    : fiber_loss_dB,
            "connector_loss_dB": connector_loss_dB,
            "splitter_loss_dB" : splitter_loss,
            "total_budget_dB"  : total_budget_dB,
            "status"           : status,
        })

    df = pd.DataFrame(results)
    cols = ["scenario", "fiber_km", "connectors", "split_ratio",
            "fiber_loss_dB", "connector_loss_dB", "splitter_loss_dB",
            "total_budget_dB", "status"]
    return df[cols]


if __name__ == "__main__":  # pragma: no cover
    from src.parsing.parse_csv import parse_csv

    print("--- Test compute_optical_budget() ---")
    tests = [
        (10.0,  16,  4),
        (14.5,  32,  6),
        (18.0,  64,  8),
        (26.0,  32, 10),
        (24.0, 128, 12),
    ]
    for km, ratio, conn in tests:
        r = compute_optical_budget(km, ratio, conn)
        print(f"  {km}km 1:{ratio} {conn}conn -> "
              f"{r['total_budget_dB']}dB [{r['status']}]")

    print("\n--- Test compute_all_scenarios() ---")
    df_opt = parse_csv("data/csv/optical_budget_scenarios.csv",
                       dtype="optical")
    df_res = compute_all_scenarios(df_opt)
    print(df_res.to_string())