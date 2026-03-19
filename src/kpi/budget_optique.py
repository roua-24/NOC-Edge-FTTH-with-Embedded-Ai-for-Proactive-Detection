"""
Module : KPI — budget_optique.py
Rôle   : Calcul du budget optique pour les topologies FTTH/GPON
         Formule : Perte_totale = perte_fibre*km + nb_splits*att_split + nb_conn*att_conn

Budget standard GPON :
    - Fibre monomode : ~0.35 dB/km
    - Splitter 1:32  : ~16 dB
    - Connecteur SC/APC : ~0.3 dB
    - Marge système : 3 dB
"""

# Constantes d'atténuation (dB)
ATT_FIBRE_DB_KM   = 0.35   # dB par km (fibre monomode G.652)
ATT_SPLITTER = {
    8:   10.0,   # 1:8   → ~10 dB
    16:  13.5,   # 1:16  → ~13.5 dB
    32:  16.0,   # 1:32  → ~16 dB (standard GPON)
    64:  19.5,   # 1:64  → ~19.5 dB
    128: 22.5,   # 1:128 → extension longue distance
    256: 25.5,   # 1:256 → scénario extrême
}
ATT_CONNECTOR_DB  = 0.3    # dB par connecteur SC/APC
MARGIN_DB         = 3.0    # Marge système
OLT_TX_POWER_DBM  = 5.0    # Puissance émission OLT (dBm)
ONT_RX_SENSITIVITY_DBM = -27.0  # Sensibilité réception ONT


def compute_optical_budget(distance_km: float, split_ratio: int,
                           nb_connectors: int = 4) -> dict:
    """
    Calcule le budget optique d'une liaison OLT→ONT.

    Parameters
    ----------
    distance_km   : float — longueur totale de fibre en km
    split_ratio   : int   — ratio du splitter (8, 16, 32, 64, 128, 256)
    nb_connectors : int   — nombre de connecteurs (défaut : 4)

    Returns
    -------
    dict avec keys : perte_fibre_db, perte_splitter_db, perte_connecteurs_db,
                     perte_totale_db, marge_disponible_db, status
    """
    perte_fibre      = ATT_FIBRE_DB_KM * distance_km
    perte_splitter   = ATT_SPLITTER.get(split_ratio, 16.0)
    perte_connecteurs= ATT_CONNECTOR_DB * nb_connectors
    perte_totale     = perte_fibre + perte_splitter + perte_connecteurs + MARGIN_DB

    budget_total     = OLT_TX_POWER_DBM - ONT_RX_SENSITIVITY_DBM
    marge_dispo      = budget_total - perte_totale

    return {
        "distance_km":        distance_km,
        "split_ratio":        split_ratio,
        "perte_fibre_db":     round(perte_fibre, 2),
        "perte_splitter_db":  round(perte_splitter, 2),
        "perte_connecteurs_db": round(perte_connecteurs, 2),
        "perte_totale_db":    round(perte_totale, 2),
        "budget_total_db":    round(budget_total, 2),
        "marge_disponible_db": round(marge_dispo, 2),
        "status":             "OK" if marge_dispo > 0 else "HORS_BUDGET",
    }
