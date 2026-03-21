import re
import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="[parse_snmp] %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# Regex : capture OID_name.instance = Type: valeur
PATTERN = re.compile(r'^([\w\-]+::[\w\.]+)\s*=\s*(\w+):\s*(.+)$')


def parse_snmp(path: str) -> pd.DataFrame:
    """
    Lit un fichier snmpwalk .txt et retourne un DataFrame.

    Args:
        path : chemin vers le fichier snmpwalk_*.txt

    Returns:
        pd.DataFrame avec colonnes :
        equipment_id, oid_name, oid_type, value, unit
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    # Déduire equipment_id depuis le nom de fichier
    # snmpwalk_olt_port_1.txt → OLT_1
    # snmpwalk_ONT_101.txt    → ONT_101
    stem = path.stem  # ex: snmpwalk_ONT_101
    if "ONT" in stem.upper():
        equipment_id = "ONT_" + stem.split("_")[-1]
    else:
        equipment_id = "OLT_1"

    logger.info(f"Parsing '{path.name}' → equipment: {equipment_id}")

    rows = []
    n_total = 0
    n_parsed = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n_total += 1

            match = PATTERN.match(line)
            if match:
                oid_full  = match.group(1)   # ex: IF-MIB::ifInOctets.1
                oid_type  = match.group(2)   # ex: Counter32
                raw_value = match.group(3).strip()

                # Extraire nom OID sans l'instance (.1, .101...)
                oid_name = oid_full.split("::")[1].split(".")[0]

                # Convertir la valeur en float si possible
                try:
                    value = float(raw_value)
                    unit  = oid_type
                except ValueError:
                    value = None
                    unit  = raw_value  # STRING, etc.

                rows.append({
                    "equipment_id": equipment_id,
                    "oid_name"    : oid_name,
                    "oid_type"    : oid_type,
                    "value"       : value,
                    "unit"        : unit,
                })
                n_parsed += 1
            else:
                logger.warning(f"Ligne non parsée : '{line}'")

    taux = n_parsed / n_total * 100 if n_total > 0 else 0
    logger.info(f"✓ {n_parsed}/{n_total} lignes parsées ({taux:.0f}%)")

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def parse_snmp_dir(snmp_dir: str) -> pd.DataFrame:
    """
    Parse tous les fichiers snmpwalk_*.txt d'un dossier.

    Args:
        snmp_dir : chemin vers le dossier snmp/

    Returns:
        pd.DataFrame consolidé de tous les équipements
    """
    snmp_dir = Path(snmp_dir)
    files    = sorted(snmp_dir.glob("snmpwalk_*.txt"))

    if not files:
        raise FileNotFoundError(f"Aucun fichier snmpwalk_*.txt dans : {snmp_dir}")

    logger.info(f"Dossier '{snmp_dir}' — {len(files)} fichiers trouvés")

    frames  = []
    succes  = 0
    for f in files:
        try:
            df = parse_snmp(str(f))
            if not df.empty:
                frames.append(df)
                succes += 1
        except Exception as e:
            logger.error(f"Erreur sur '{f.name}' : {e}")

    taux = succes / len(files) * 100
    logger.info(f"✓ {succes}/{len(files)} fichiers parsés ({taux:.0f}%)")

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__": # pragma: no cover
    print("─── Test parse_snmp() — fichier OLT ───")
    df_olt = parse_snmp("data/snmp/snmpwalk_olt_port_1.txt")
    print(df_olt.to_string())

    print("\n─── Test parse_snmp() — ONT_101 ───")
    df_ont = parse_snmp("data/snmp/snmpwalk_ONT_101.txt")
    print(df_ont.to_string())

    print("\n─── Test parse_snmp_dir() — tous les fichiers ───")
    df_all = parse_snmp_dir("data/snmp")
    print(f"Shape total : {df_all.shape}")
    print(f"Équipements : {df_all['equipment_id'].nunique()}")
    print(df_all.head(5).to_string())

    n_eq   = df_all["equipment_id"].nunique()
    taux   = n_eq / 101 * 100
    print(f"\nRésultat : {n_eq}/101 équipements parsés ({taux:.0f}%)")
    print(f"CDC ≥ 90% : {'OK' if taux >= 90 else 'ERREUR'}")