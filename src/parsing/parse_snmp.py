"""
Module : PARSING — parse_snmp.py
Rôle   : Lire les fichiers snmpwalk .txt et extraire les OIDs/valeurs
Entrée : chemin vers un fichier .txt (snmpwalk output)
Sortie : pandas.DataFrame avec colonnes normalisées

Format snmpwalk attendu :
    IF-MIB::ifInOctets.1 = Counter32: 1234567890
    IF-MIB::ifOutOctets.1 = Counter32: 987654321
    ...

Colonnes produites :
    oid        (str)   — OID complet (ex: IF-MIB::ifInOctets.1)
    oid_name   (str)   — nom MIB (ex: ifInOctets)
    instance   (str)   — instance (ex: .1 = port/interface)
    type       (str)   — type SNMP (Counter32, Gauge32, INTEGER, STRING...)
    value      (str)   — valeur brute
    value_int  (int)   — valeur numérique (NaN si non applicable)
    device     (str)   — nom du fichier source (identifiant équipement)
"""

import re
import pandas as pd
from pathlib import Path


# ── Regex patterns ───────────────────────────────────────────────────────────
_SNMPWALK_RE = re.compile(
    r"^(?P<oid>[^\s]+)\s*=\s*(?P<type>[^:]+):\s*(?P<value>.+)$"
)
_OID_SPLIT_RE = re.compile(r"^(?P<name>[A-Za-z:]+)\.(?P<instance>.+)$")


def parse_snmp(filepath: str | Path) -> pd.DataFrame:
    """
    Parse un fichier snmpwalk .txt et retourne un DataFrame normalisé.

    Parameters
    ----------
    filepath : str | Path
        Chemin vers le fichier snmpwalk .txt.

    Returns
    -------
    pd.DataFrame
        Colonnes : oid, oid_name, instance, type, value, value_int, device.
    """
    # TODO S3 : implémenter
    # filepath = Path(filepath)
    # rows = []
    # with open(filepath, "r", encoding="utf-8", errors="replace") as f:
    #     for line in f:
    #         m = _SNMPWALK_RE.match(line.strip())
    #         if not m:
    #             continue
    #         oid   = m.group("oid")
    #         stype = m.group("type").strip()
    #         value = m.group("value").strip()
    #         split = _OID_SPLIT_RE.match(oid)
    #         oid_name = split.group("name") if split else oid
    #         instance = split.group("instance") if split else ""
    #         try:
    #             value_int = int(value)
    #         except ValueError:
    #             value_int = float("nan")
    #         rows.append(dict(oid=oid, oid_name=oid_name, instance=instance,
    #                          type=stype, value=value, value_int=value_int,
    #                          device=filepath.stem))
    # return pd.DataFrame(rows)
    raise NotImplementedError("parse_snmp — implémentation prévue en S3")


def parse_snmp_dir(dirpath: str | Path) -> pd.DataFrame:
    """Parse tous les .txt d'un répertoire SNMP et concatène les résultats."""
    # TODO S3
    raise NotImplementedError
