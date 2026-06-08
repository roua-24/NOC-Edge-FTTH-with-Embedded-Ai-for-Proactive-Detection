"""
Module Securite SNMP -- Rapport de Conformite
==============================================
§9 CDC : Generation du rapport de conformite securite SNMP.

Produit deux sorties depuis le dict retourne par audit_snmp() :
    1. rapport_conformite_SNMP.txt  -- rapport lisible (jury / encadrement)
    2. rapport_conformite_SNMP.json -- donnees structurees (archivage / pipeline)

Interface publique :
    generate_conformity_report(rapport, output_dir) -> dict[str, Path]

Auteur  : Roua Jendoubi
Sprint  : S9
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constantes de mise en forme
# -----------------------------------------------------------------------------
_SEP_DOUBLE = "=" * 70
_SEP_SIMPLE = "-" * 70

_BADGE = {
    "CONFORME":               "[OK]     CONFORME",
    "PARTIELLEMENT CONFORME": "[ALERTE] PARTIELLEMENT CONFORME",
    "NON CONFORME":           "[ECHEC]  NON CONFORME",
}

_TXT_FILENAME  = "rapport_conformite_SNMP.txt"
_JSON_FILENAME = "rapport_conformite_SNMP.json"


# -----------------------------------------------------------------------------
# Helpers internes
# -----------------------------------------------------------------------------

def _score_bar(score: int, width: int = 40) -> str:
    """Genere une barre de progression ASCII pour le score 0-100."""
    filled = round(score * width / 100)
    empty  = width - filled
    bar    = "#" * filled + "." * empty
    return "[{}] {}/100".format(bar, score)


def _bool_label(value: bool, label_ok: str, label_ko: str) -> str:
    """Retourne un label textuel selon une valeur booleenne."""
    return label_ok if value else label_ko


def _build_txt_report(rapport: dict, generated_at: str) -> str:
    """
    Construit le contenu textuel du rapport de conformite.

    Format structure lisible par le jury et l'encadrement.
    """
    lines: list[str] = []

    # -- En-tete --------------------------------------------------------------
    lines += [
        _SEP_DOUBLE,
        "  NOC-Edge FTTH - RAPPORT DE CONFORMITE SECURITE SNMP",
        "  §9 CDC : Audit SNMPv2c vs SNMPv3 | Baseline authPriv",
        _SEP_DOUBLE,
        "  Genere le    : {}".format(generated_at),
        "  Fichiers analyses : {}".format(rapport.get("nb_files", 0)),
        _SEP_DOUBLE,
        "",
    ]

    # -- Score global ---------------------------------------------------------
    score      = rapport.get("score", 0)
    conformity = rapport.get("conformity", "NON CONFORME")
    badge      = _BADGE.get(conformity, conformity)

    lines += [
        "  SCORE DE CONFORMITE GLOBAL",
        _SEP_SIMPLE,
        "  {}".format(_score_bar(score)),
        "  Niveau : {}".format(badge),
        "",
        "  Seuils (§9 CDC) :",
        "    >= 80/100  :  CONFORME",
        "    50-79/100  :  PARTIELLEMENT CONFORME",
        "    <  50/100  :  NON CONFORME",
        "",
    ]

    # -- Statistiques reseau --------------------------------------------------
    nb_v2c     = rapport.get("nb_v2c", 0)
    nb_authpriv = rapport.get("nb_authpriv", 0)
    lines += [
        "  STATISTIQUES DU RESEAU AUDITE",
        _SEP_SIMPLE,
        "  Equipements SNMPv2c      : {}  {}".format(
            nb_v2c, "[ALERTE]" if nb_v2c > 0 else "[OK]"
        ),
        "  Equipements SNMPv3       : {}".format(rapport.get("nb_v3", 0)),
        "  Equipements authPriv     : {}  {}".format(
            nb_authpriv, "[OK]" if nb_authpriv > 0 else "[NON CONFIGURE]"
        ),
        "",
    ]

    # -- Resultats par equipement ---------------------------------------------
    devices = rapport.get("devices", [])
    if devices:
        lines += ["  DETAIL PAR EQUIPEMENT", _SEP_SIMPLE]
        for dev in devices:
            fname   = dev.get("filename", "inconnu")
            dscore  = dev.get("device_score", 0)
            v2c     = _bool_label(dev.get("has_v2c"),    "SNMPv2c : OUI [ALERTE]", "SNMPv2c : NON")
            v3      = _bool_label(dev.get("has_v3"),     "SNMPv3  : OUI", "SNMPv3  : NON")
            ap      = _bool_label(dev.get("has_authpriv"), "authPriv : OUI [OK]", "authPriv : NON [ALERTE]")
            sha     = _bool_label(dev.get("has_sha"),    "SHA-256 : OUI", "SHA-256 : NON")
            aes     = _bool_label(dev.get("has_aes"),    "AES-256 : OUI", "AES-256 : NON")
            comms   = ", ".join(dev.get("communities", [])) or "aucune"

            lines += [
                "",
                "  [{}]  Score : {}/100".format(fname, dscore),
                "    {}  |  {}  |  {}".format(v2c, v3, ap),
                "    {}  |  {}".format(sha, aes),
                "    Community strings : {}".format(comms),
            ]
            for alert in dev.get("alerts", []):
                lines.append("    [!] {}".format(alert))
        lines.append("")

    # -- Alertes consolidees --------------------------------------------------
    alerts = rapport.get("alerts", [])
    lines += ["  ALERTES DE SECURITE CONSOLIDEES", _SEP_SIMPLE]
    if alerts:
        for alert in alerts:
            lines.append("  - {}".format(alert))
    else:
        lines.append("  Aucune alerte - Infrastructure conforme.")
    lines.append("")

    # -- Recommandations ------------------------------------------------------
    recommendations = rapport.get("recommendations", [])
    lines += ["  RECOMMANDATIONS BASELINE authPriv (§9 CDC)", _SEP_SIMPLE]
    for i, rec in enumerate(recommendations, 1):
        lines.append("  {}. {}".format(i, rec))
    lines.append("")

    # -- Baseline de reference ------------------------------------------------
    baseline = rapport.get("baseline", {})
    if baseline:
        lines += ["  BASELINE DE REFERENCE SNMPv3 authPriv", _SEP_SIMPLE]
        excluded = {
            "description", "reference", "compliance_thresholds",
            "weak_communities", "prohibited_protocols",
            "prohibited_auth_protocols", "prohibited_priv_protocols",
        }
        for key, val in baseline.items():
            if key not in excluded:
                lines.append("  {:<35} : {}".format(key, val))
        ref = baseline.get("reference", "")
        if ref:
            lines.append("  Reference : {}".format(ref))
        lines.append("")

    # -- Pied de page ---------------------------------------------------------
    lines += [
        _SEP_DOUBLE,
        "  NOC-Edge FTTH  -  Projet academique  -  Usage pedagogique uniquement",
        "  Module Securite SNMP  -  §9 CDC  -  Roua Jendoubi",
        _SEP_DOUBLE,
    ]

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Interface publique
# -----------------------------------------------------------------------------

def generate_conformity_report(
    rapport: dict,
    output_dir: "str | Path" = "reports",
) -> dict[str, Path]:
    """
    Genere le rapport de conformite securite SNMP sur disque.

    Produit depuis le dict retourne par audit_snmp() :
      - rapport_conformite_SNMP.txt  : rapport lisible (jury)
      - rapport_conformite_SNMP.json : donnees structurees (archivage)

    §9 CDC : "Rapport de conformite (score)" -- livrable module Securite.

    Args:
        rapport    : dict retourne par audit_snmp().
        output_dir : repertoire de sortie (cree si absent).
                     Defaut : reports/

    Returns:
        dict avec cles 'txt' et 'json' pointant vers les Path generes.

    Raises:
        ValueError : si rapport est vide ou ne contient pas la cle 'score'.
        OSError    : si le repertoire ne peut pas etre cree.
    """
    if not rapport:
        raise ValueError("Le rapport est vide -- executer audit_snmp() d'abord.")
    if "score" not in rapport:
        raise ValueError(
            "Cle 'score' absente du rapport -- rapport invalide."
        )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -- 1. Rapport TXT -------------------------------------------------------
    txt_content = _build_txt_report(rapport, generated_at)
    txt_file    = out_path / _TXT_FILENAME
    txt_file.write_text(txt_content, encoding="utf-8")
    logger.info("Rapport TXT genere : %s", txt_file)

    # -- 2. Rapport JSON ------------------------------------------------------
    export_data = {
        "meta": {
            "generated_at":  generated_at,
            "module":        "Securite SNMP",
            "sprint":        "S9",
            "cdc_reference": "§9 -- Securite & conformite",
        },
        **rapport,
    }
    json_file = out_path / _JSON_FILENAME
    json_file.write_text(
        json.dumps(export_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Rapport JSON genere : %s", json_file)

    logger.info(
        "Rapport de conformite genere -- Score : %d/100 (%s)",
        rapport.get("score", 0),
        rapport.get("conformity", "-"),
    )

    return {"txt": txt_file, "json": json_file}