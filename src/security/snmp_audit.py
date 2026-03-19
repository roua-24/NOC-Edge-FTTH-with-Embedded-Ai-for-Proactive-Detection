"""
Module : SÉCURITÉ — snmp_audit.py
Rôle   : Audit des fichiers SNMP (détection v2c, recommandations v3 authPriv)
Sortie : rapport_conformite dict avec score, alertes et recommandations
"""
import re
from pathlib import Path


V2C_MARKERS  = ["community", "public", "private", "SNMPv2"]
V3_MARKERS   = ["authPriv", "SHA", "AES", "usmUser"]
BASELINES = {
    "auth_protocol":  "SHA-256",
    "priv_protocol":  "AES-256",
    "security_level": "authPriv",
    "min_version":    "SNMPv3",
}


def audit_snmp(snmp_dir: str | Path) -> dict:
    """
    Analyse tous les fichiers .txt du répertoire SNMP.

    Returns
    -------
    dict :
        score          (int)  — score de conformité 0-100
        alerts         (list) — liste des alertes détectées
        recommendations(list) — recommandations baseline v3
        files_audited  (int)
        v2c_count      (int)  — fichiers avec indices SNMPv2c
        v3_count       (int)  — fichiers conformes SNMPv3
    """
    snmp_dir = Path(snmp_dir)
    files = list(snmp_dir.glob("*.txt"))
    alerts = []
    v2c_count = v3_count = 0

    for f in files:
        content = f.read_text(encoding="utf-8", errors="replace").lower()
        is_v2c = any(m.lower() in content for m in V2C_MARKERS)
        is_v3  = any(m.lower() in content for m in V3_MARKERS)
        if is_v2c and not is_v3:
            v2c_count += 1
            alerts.append(f"⚠️  {f.name} : SNMPv2c détecté — community string en clair")
        elif is_v3:
            v3_count += 1

    total = len(files)
    score = int((v3_count / total * 100)) if total > 0 else 0

    recommendations = [
        f"Migrer {v2c_count} équipement(s) de SNMPv2c vers SNMPv3",
        f"Configurer auth_protocol={BASELINES['auth_protocol']}",
        f"Configurer priv_protocol={BASELINES['priv_protocol']}",
        "Activer security_level=authPriv sur tous les agents SNMP",
        "Supprimer les community strings 'public' et 'private'",
    ] if v2c_count > 0 else ["✅ Tous les équipements utilisent SNMPv3 authPriv"]

    return {
        "score":            score,
        "alerts":           alerts,
        "recommendations":  recommendations,
        "files_audited":    total,
        "v2c_count":        v2c_count,
        "v3_count":         v3_count,
        "baselines":        BASELINES,
    }
