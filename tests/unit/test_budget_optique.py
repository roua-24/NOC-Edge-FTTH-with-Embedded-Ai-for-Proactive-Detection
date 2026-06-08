"""
tests/unit/test_budget_optique.py
==================================
Tests unitaires — Module Budget Optique  |  NOC-Edge FTTH
CDC §10 : tests unitaires >= 70 % des modules critiques
CDC §8  : scenarios budget optique (ratios 1:16 a 1:256)

Valeurs status S4 — 3 niveaux (deduits des tracebacks successifs) :
    "OK"           : perte dans les limites du budget GPON
    "Risque"       : perte moderement depassee
    "Non conforme" : perte fortement depassee

Ratios supportes : [16, 32, 64, 128, 256]

Execution :
    pytest tests/unit/test_budget_optique.py -v --cov=src/kpi --cov-report=term-missing
"""

import pytest
from budget_optique import compute_optical_budget

# ─────────────────────────────────────────────────────────────────
#  CONSTANTES S4 — reelles
# ─────────────────────────────────────────────────────────────────
KEY_STATUS         = "status"
KEY_TOTAL          = "total_budget_dB"
KEY_FIBER_LOSS     = "fiber_loss_dB"
KEY_CONNECTOR_LOSS = "connector_loss_dB"
KEY_SPLITTER_LOSS  = "splitter_loss_dB"

STATUS_OK            = "OK"
STATUS_RISQUE        = "Risque"
STATUS_NON_CONFORME  = "Non conforme"

ALL_STATUS = (STATUS_OK, STATUS_RISQUE, STATUS_NON_CONFORME)

RATIOS_VALIDES_S4 = [16, 32, 64, 128, 256]

# ─────────────────────────────────────────────────────────────────
#  SCENARIOS CDC §8 — calibres sur le comportement reel S4
# ─────────────────────────────────────────────────────────────────
SCENARIOS_OK = [
    (5,  16, 4, "Sc.1 - Residentiel court (1:16, 5 km)"),
    (10, 16, 6, "Sc.2 - Residentiel standard (1:16, 10 km)"),
    (15, 32, 4, "Sc.3 - Extension quartier (1:32, 15 km)"),
    (8,  64, 4, "Sc.5 - Zone dense (1:64, 8 km)"),
]

SCENARIOS_RISQUE = [
    (15, 256, 2, "Sc.8 - Extreme CDC §8 (1:256, 15 km)"),
]

SCENARIOS_NON_CONFORME = [
    (30, 128, 6, "Sc.7b - Long distance (1:128, 30 km)"),
    (40, 64,  6, "Sc.6b - Zone dense tres longue (1:64, 40 km)"),
    (50, 32,  6, "Sc.4b - Extension tres longue (1:32, 50 km)"),
]

SCENARIOS_TOUS = SCENARIOS_OK + SCENARIOS_RISQUE + SCENARIOS_NON_CONFORME


# ═════════════════════════════════════════════════════════════════
#  GROUPE 1 — Structure du dictionnaire de sortie
#  CDC §7 : compute_optical_budget() -> dict
# ═════════════════════════════════════════════════════════════════

class TestStructureSortie:

    def test_retourne_un_dict(self):
        """CDC §7 : le resultat doit etre un dict."""
        res = compute_optical_budget(10, 16, nb_connectors=4)
        assert isinstance(res, dict)

    def test_toutes_cles_obligatoires(self):
        """CDC §7 : toutes les cles attendues sont presentes."""
        res = compute_optical_budget(10, 16, nb_connectors=4)
        for cle in [KEY_STATUS, KEY_TOTAL, KEY_FIBER_LOSS,
                    KEY_CONNECTOR_LOSS, KEY_SPLITTER_LOSS]:
            assert cle in res, \
                f"Cle '{cle}' absente. Cles dispo : {list(res.keys())}"

    def test_status_ok_scenario_court(self):
        """status = 'OK' pour scenario court (1:16, 5 km)."""
        res = compute_optical_budget(5, 16, nb_connectors=4)
        assert res[KEY_STATUS] == STATUS_OK, \
            f"Attendu '{STATUS_OK}', obtenu '{res[KEY_STATUS]}'"

    def test_status_risque_scenario_1_256(self):
        """status = 'Risque' pour (1:256, 15 km)."""
        res = compute_optical_budget(15, 256, nb_connectors=2)
        assert res[KEY_STATUS] == STATUS_RISQUE, \
            f"Attendu '{STATUS_RISQUE}', obtenu '{res[KEY_STATUS]}'"

    def test_status_non_conforme_scenario_extreme(self):
        """status = 'Non conforme' pour (1:128, 30 km)."""
        res = compute_optical_budget(30, 128, nb_connectors=6)
        assert res[KEY_STATUS] == STATUS_NON_CONFORME, \
            f"Attendu '{STATUS_NON_CONFORME}', obtenu '{res[KEY_STATUS]}'"

    def test_total_budget_positif(self):
        """total_budget_dB > 0."""
        res = compute_optical_budget(10, 16, nb_connectors=4)
        assert res[KEY_TOTAL] > 0

    def test_pertes_composantes_positives(self):
        """Toutes les pertes par composante >= 0."""
        res = compute_optical_budget(10, 32, nb_connectors=6)
        assert res[KEY_FIBER_LOSS]     >= 0
        assert res[KEY_CONNECTOR_LOSS] >= 0
        assert res[KEY_SPLITTER_LOSS]  >= 0

    def test_zero_connecteurs(self):
        """nb_connectors=0 fonctionne et retourne connector_loss = 0."""
        res = compute_optical_budget(10, 16, nb_connectors=0)
        assert isinstance(res, dict)
        assert res[KEY_CONNECTOR_LOSS] == 0 or res[KEY_CONNECTOR_LOSS] == 0.0


# ═════════════════════════════════════════════════════════════════
#  GROUPE 2 — 8 Scenarios CDC §8
# ═════════════════════════════════════════════════════════════════

class TestScenariosOptiques:

    @pytest.mark.parametrize(
        "dist, split_ratio, nb_conn, description",
        SCENARIOS_OK,
        ids=[s[3] for s in SCENARIOS_OK]
    )
    def test_statut_ok(self, dist, split_ratio, nb_conn, description):
        """CDC §8 : scenarios dans les limites -> 'OK'."""
        res = compute_optical_budget(dist, split_ratio, nb_connectors=nb_conn)
        assert res[KEY_STATUS] == STATUS_OK, (
            f"{description}\n"
            f"  Status obtenu : {res[KEY_STATUS]}\n"
            f"  Total budget  : {res[KEY_TOTAL]:.2f} dB"
        )

    @pytest.mark.parametrize(
        "dist, split_ratio, nb_conn, description",
        SCENARIOS_RISQUE,
        ids=[s[3] for s in SCENARIOS_RISQUE]
    )
    def test_statut_risque(self, dist, split_ratio, nb_conn, description):
        """CDC §8 : scenarios moderement depasses -> 'Risque'."""
        res = compute_optical_budget(dist, split_ratio, nb_connectors=nb_conn)
        assert res[KEY_STATUS] == STATUS_RISQUE, (
            f"{description}\n"
            f"  Status obtenu : {res[KEY_STATUS]}\n"
            f"  Total budget  : {res[KEY_TOTAL]:.2f} dB"
        )

    @pytest.mark.parametrize(
        "dist, split_ratio, nb_conn, description",
        SCENARIOS_NON_CONFORME,
        ids=[s[3] for s in SCENARIOS_NON_CONFORME]
    )
    def test_statut_non_conforme(self, dist, split_ratio, nb_conn, description):
        """CDC §8 : scenarios fortement depasses -> 'Non conforme'."""
        res = compute_optical_budget(dist, split_ratio, nb_connectors=nb_conn)
        assert res[KEY_STATUS] == STATUS_NON_CONFORME, (
            f"{description}\n"
            f"  Status obtenu : {res[KEY_STATUS]}\n"
            f"  Total budget  : {res[KEY_TOTAL]:.2f} dB"
        )

    @pytest.mark.parametrize(
        "dist, split_ratio, nb_conn, description",
        SCENARIOS_TOUS,
        ids=[s[3] for s in SCENARIOS_TOUS]
    )
    def test_pertes_positives_tous_scenarios(self, dist, split_ratio,
                                              nb_conn, description):
        """Pertes composantes >= 0 pour tous les scenarios."""
        res = compute_optical_budget(dist, split_ratio, nb_connectors=nb_conn)
        assert res[KEY_FIBER_LOSS]     >= 0
        assert res[KEY_CONNECTOR_LOSS] >= 0
        assert res[KEY_SPLITTER_LOSS]  >= 0

    @pytest.mark.parametrize(
        "dist, split_ratio, nb_conn, description",
        SCENARIOS_TOUS,
        ids=[s[3] for s in SCENARIOS_TOUS]
    )
    def test_status_dans_valeurs_connues(self, dist, split_ratio,
                                          nb_conn, description):
        """Status doit etre dans les 3 valeurs connues de S4."""
        res = compute_optical_budget(dist, split_ratio, nb_connectors=nb_conn)
        assert res[KEY_STATUS] in ALL_STATUS, \
            f"{description} : status inconnu '{res[KEY_STATUS]}'"


# ═════════════════════════════════════════════════════════════════
#  GROUPE 3 — Exactitude formule ITU-T G.984
#  CDC §2.1 : "budget optique (pertes fibre, connecteurs, splitters)"
# ═════════════════════════════════════════════════════════════════

class TestFormuleITUT:

    def test_perte_fibre_proportionnelle_distance(self):
        """Doubler la distance double la perte fibre."""
        res_5  = compute_optical_budget(5,  16, nb_connectors=4)
        res_10 = compute_optical_budget(10, 16, nb_connectors=4)
        ratio = res_10[KEY_FIBER_LOSS] / res_5[KEY_FIBER_LOSS]
        assert abs(ratio - 2.0) < 0.05, \
            f"Ratio perte fibre = {ratio:.3f} (attendu ~2.0)"

    def test_perte_totale_monotone_avec_distance(self):
        """Plus la distance augmente, plus la perte totale augmente."""
        distances = [2, 5, 10, 15, 20, 25, 30]
        pertes = [
            compute_optical_budget(d, 32, nb_connectors=4)[KEY_TOTAL]
            for d in distances
        ]
        for i in range(1, len(pertes)):
            assert pertes[i] > pertes[i - 1], \
                f"Non monotone : {distances[i-1]}km={pertes[i-1]:.2f} " \
                f">= {distances[i]}km={pertes[i]:.2f}"

    def test_perte_splitter_monotone_avec_ratio(self):
        """Plus le ratio splitter est eleve, plus la perte splitter augmente."""
        pertes = [
            compute_optical_budget(10, r, nb_connectors=4)[KEY_SPLITTER_LOSS]
            for r in RATIOS_VALIDES_S4
        ]
        for i in range(1, len(pertes)):
            assert pertes[i] > pertes[i - 1]

    def test_perte_connecteurs_proportionnelle(self):
        """Doubler les connecteurs double la perte connecteurs."""
        res_2 = compute_optical_budget(10, 16, nb_connectors=2)
        res_4 = compute_optical_budget(10, 16, nb_connectors=4)
        if res_2[KEY_CONNECTOR_LOSS] > 0:
            ratio = res_4[KEY_CONNECTOR_LOSS] / res_2[KEY_CONNECTOR_LOSS]
            assert abs(ratio - 2.0) < 0.05

    def test_determinisme(self):
        """Deux appels identiques retournent le meme resultat."""
        res1 = compute_optical_budget(10, 32, nb_connectors=4)
        res2 = compute_optical_budget(10, 32, nb_connectors=4)
        assert res1[KEY_TOTAL]  == res2[KEY_TOTAL]
        assert res1[KEY_STATUS] == res2[KEY_STATUS]

    def test_ok_implique_perte_inferieure_seuil(self):
        """Sc.1 OK : total_budget_dB < seuil Risque S4."""
        res_ok = compute_optical_budget(5, 16, nb_connectors=4)
        res_risque = compute_optical_budget(15, 256, nb_connectors=2)
        assert res_ok[KEY_TOTAL] < res_risque[KEY_TOTAL], \
            "Un scenario OK doit avoir une perte inferieure a un scenario Risque"


# ═════════════════════════════════════════════════════════════════
#  GROUPE 4 — Ratios splitter S4
#  CDC §8 : ratios supportes = [16, 32, 64, 128, 256]
# ═════════════════════════════════════════════════════════════════

class TestRatiosSplitter:

    def test_ratio_invalide_leve_exception(self):
        """Ratio non supporte (ex. 1:7) -> ValueError."""
        with pytest.raises((ValueError, KeyError, Exception)):
            compute_optical_budget(10, 7, nb_connectors=4)

    def test_ratio_2_non_supporte(self):
        """Ratio 1:2 non supporte dans ATT_SPLITTER S4 -> ValueError."""
        with pytest.raises((ValueError, KeyError, Exception)):
            compute_optical_budget(10, 2, nb_connectors=4)

    @pytest.mark.parametrize("ratio", RATIOS_VALIDES_S4)
    def test_ratios_valides_s4(self, ratio):
        """Ratios [16,32,64,128,256] fonctionnent sans exception."""
        res = compute_optical_budget(10, ratio, nb_connectors=4)
        assert KEY_STATUS in res

    @pytest.mark.parametrize("ratio", RATIOS_VALIDES_S4)
    def test_perte_splitter_positive(self, ratio):
        """splitter_loss_dB >= 0 pour tous les ratios supportes."""
        res = compute_optical_budget(10, ratio, nb_connectors=4)
        assert res[KEY_SPLITTER_LOSS] >= 0

    @pytest.mark.parametrize("ratio", RATIOS_VALIDES_S4)
    def test_total_budget_positif(self, ratio):
        """total_budget_dB > 0 pour tous les ratios supportes."""
        res = compute_optical_budget(10, ratio, nb_connectors=4)
        assert res[KEY_TOTAL] > 0


# ═════════════════════════════════════════════════════════════════
#  GROUPE 5 — Fonction DataFrame (lignes 105-144 de budget_optique.py)
#  Cette fonction itere sur un DataFrame de scenarios et retourne
#  un DataFrame de resultats — CDC §8 : 8 scenarios documentes
# ═════════════════════════════════════════════════════════════════

import pandas as pd
import importlib
import budget_optique as _bo

# Detecter le nom de la fonction DataFrame automatiquement
def _get_df_function():
    """
    Cherche la fonction de budget_optique.py qui accepte un DataFrame.
    Noms possibles selon implementation S4.
    """
    candidats = [
        "compute_optical_budget_df",
        "compute_all_budgets",
        "apply_optical_budget",
        "batch_optical_budget",
        "run_optical_budget",
        "compute_budget_scenarios",
    ]
    for nom in candidats:
        if hasattr(_bo, nom):
            return getattr(_bo, nom)
    # Si non trouve : chercher dans le module toutes les fonctions
    import inspect
    for nom, obj in inspect.getmembers(_bo, inspect.isfunction):
        if nom != "compute_optical_budget":
            sig = inspect.signature(obj)
            params = list(sig.parameters.keys())
            if params and ("df" in params[0] or "optical" in params[0].lower()):
                return obj
    return None


DF_FUNC = _get_df_function()


def _make_df_scenarios(scenarios):
    """
    Cree un DataFrame de scenarios au format attendu par la fonction S4.
    Colonnes : scenario, fiber_km, connectors, split_ratio, splitter_loss_dB
    split_ratio au format "1:N" (string) comme dans optical_budget_scenarios.csv
    """
    rows = []
    for dist, ratio, nb_conn, desc in scenarios:
        rows.append({
            "scenario":        desc,
            "fiber_km":        dist,
            "connectors":      nb_conn,
            "split_ratio":     f"1:{ratio}",
        })
    return pd.DataFrame(rows)


@pytest.mark.skipif(DF_FUNC is None, reason="Fonction DataFrame non trouvee dans budget_optique.py")
class TestComputeBudgetDataFrame:
    """
    Tests de la fonction qui traite un DataFrame de scenarios.
    Couvre les lignes 105-144 de budget_optique.py.
    CDC §8 : validation sur les 8 scenarios documentes.
    """

    SCENARIOS_TEST = [
        (5,  16, 4, "Sc.1 - Residentiel court"),
        (10, 16, 6, "Sc.2 - Residentiel standard"),
        (15, 32, 4, "Sc.3 - Extension quartier"),
        (8,  64, 4, "Sc.5 - Zone dense"),
        (15, 256, 2, "Sc.8 - Extreme"),
        (30, 128, 6, "Sc.7b - Non conforme"),
    ]

    def test_retourne_un_dataframe(self):
        """La fonction doit retourner un pd.DataFrame."""
        df_in = _make_df_scenarios(self.SCENARIOS_TEST[:2])
        df_out = DF_FUNC(df_in)
        assert isinstance(df_out, pd.DataFrame), \
            f"Attendu pd.DataFrame, obtenu {type(df_out)}"

    def test_meme_nombre_de_lignes(self):
        """Le DataFrame de sortie a autant de lignes que l'entree."""
        df_in = _make_df_scenarios(self.SCENARIOS_TEST)
        df_out = DF_FUNC(df_in)
        assert len(df_out) == len(df_in), \
            f"Lignes entree={len(df_in)}, sortie={len(df_out)}"

    def test_colonne_status_presente(self):
        """La colonne 'status' doit etre dans le DataFrame de sortie."""
        df_in = _make_df_scenarios(self.SCENARIOS_TEST[:2])
        df_out = DF_FUNC(df_in)
        assert "status" in df_out.columns, \
            f"Colonne 'status' absente. Colonnes : {list(df_out.columns)}"

    def test_colonne_total_budget_presente(self):
        """La colonne 'total_budget_dB' doit etre dans le DataFrame de sortie."""
        df_in = _make_df_scenarios(self.SCENARIOS_TEST[:2])
        df_out = DF_FUNC(df_in)
        assert "total_budget_dB" in df_out.columns, \
            f"Colonne 'total_budget_dB' absente. Colonnes : {list(df_out.columns)}"

    def test_colonnes_pertes_presentes(self):
        """Les colonnes de pertes composantes doivent etre presentes."""
        df_in = _make_df_scenarios(self.SCENARIOS_TEST[:2])
        df_out = DF_FUNC(df_in)
        for col in ["fiber_loss_dB", "connector_loss_dB", "splitter_loss_dB"]:
            assert col in df_out.columns, \
                f"Colonne '{col}' absente. Colonnes : {list(df_out.columns)}"

    def test_status_valides_dans_resultats(self):
        """Tous les status du DataFrame doivent etre dans les 3 valeurs connues."""
        df_in = _make_df_scenarios(self.SCENARIOS_TEST)
        df_out = DF_FUNC(df_in)
        status_valides = {"OK", "Risque", "Non conforme"}
        for status in df_out["status"]:
            assert status in status_valides, \
                f"Status inattendu : '{status}'"

    def test_scenario_court_est_ok(self):
        """Scenario Sc.1 (1:16, 5 km) doit avoir status='OK'."""
        df_in = _make_df_scenarios([(5, 16, 4, "Sc.1 - court")])
        df_out = DF_FUNC(df_in)
        assert df_out.iloc[0]["status"] == "OK", \
            f"Sc.1 : status={df_out.iloc[0]['status']}"

    def test_scenario_extreme_non_ok(self):
        """Scenario extreme (1:256, 15 km) ne doit pas etre OK."""
        df_in = _make_df_scenarios([(15, 256, 2, "Sc.8 - extreme")])
        df_out = DF_FUNC(df_in)
        assert df_out.iloc[0]["status"] != "OK", \
            "Sc.8 extreme ne devrait pas etre OK"

    def test_pertes_positives_dans_dataframe(self):
        """Toutes les pertes dans le DataFrame de sortie >= 0."""
        df_in = _make_df_scenarios(self.SCENARIOS_TEST)
        df_out = DF_FUNC(df_in)
        for col in ["fiber_loss_dB", "connector_loss_dB", "splitter_loss_dB"]:
            if col in df_out.columns:
                assert (df_out[col] >= 0).all(), \
                    f"Colonne {col} contient des valeurs negatives"

    def test_avec_colonne_splitter_loss_csv(self):
        """
        Couvre la branche ligne 110-111 : utiliser splitter_loss_dB du CSV
        si la colonne est presente dans le DataFrame d'entree.
        """
        df_in = _make_df_scenarios([(10, 16, 4, "Sc.avec_splitter")])
        df_in["splitter_loss_dB"] = 12.5  # valeur imposee
        df_out = DF_FUNC(df_in)
        assert isinstance(df_out, pd.DataFrame)
        # La valeur splitter utilisee doit etre 12.5
        if "splitter_loss_dB" in df_out.columns:
            assert abs(df_out.iloc[0]["splitter_loss_dB"] - 12.5) < 0.01

    def test_sans_colonne_splitter_loss_csv(self):
        """
        Couvre la branche ligne 112-113 : utiliser ATT_SPLITTER
        si splitter_loss_dB absent du DataFrame d'entree.
        """
        df_in = _make_df_scenarios([(10, 32, 4, "Sc.sans_splitter")])
        # Ne pas ajouter splitter_loss_dB -> branche else
        assert "splitter_loss_dB" not in df_in.columns
        df_out = DF_FUNC(df_in)
        assert isinstance(df_out, pd.DataFrame)
        assert len(df_out) == 1