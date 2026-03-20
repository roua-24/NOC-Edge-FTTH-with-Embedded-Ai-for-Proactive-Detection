import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="[parse_pcap] %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Colonnes attendues dans pcap_flows_summary.csv
REQUIRED_COLS = ["timestamp", "src_ip", "dst_ip",
                 "protocol", "packets", "bytes", "label_suspicious"]


def parse_pcap(path: str) -> pd.DataFrame:
    """
    Lit un fichier de flux PCAP (format CSV simulé) et retourne
    un DataFrame normalisé.

    Note : le dataset utilise un résumé CSV des flux réseau
    (pcap_flows_summary.csv) car les fichiers .pcap binaires
    nécessitent Scapy et une infrastructure réseau réelle.
    Ce parseur lit le résumé synthétique produit par l'encadrant.

    Args:
        path : chemin vers pcap_flows_summary.csv

    Returns:
        pd.DataFrame avec colonnes :
        timestamp, src_ip, dst_ip, protocol,
        packets, bytes, label_suspicious
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    logger.info(f"Lecture '{path.name}'...")

    try:
        df = pd.read_csv(path, parse_dates=["timestamp"])

        # Validation colonnes obligatoires
        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            raise ValueError(f"Colonnes manquantes : {missing}")

        # Gestion NaN
        n_nan = df.isnull().sum().sum()
        if n_nan > 0:
            logger.warning(f"{n_nan} NaN detectes - application ffill()")
            df = df.ffill().dropna()

        # Tri chronologique
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Optimisation types
        df["protocol"] = df["protocol"].astype("category")
        df["packets"]  = df["packets"].astype("int32")
        df["bytes"]    = df["bytes"].astype("int32")

        n_suspicious = df["label_suspicious"].sum()
        logger.info(f"[OK] {len(df):,} flux | "
                    f"suspects : {n_suspicious} ({n_suspicious/len(df)*100:.1f}%)")

        return df

    except pd.errors.ParserError as e:
        logger.error(f"Erreur parsing : {e}")
        return pd.DataFrame()


if __name__ == "__main__":
    print("--- Test parse_pcap() ---")
    df = parse_pcap("data/traces/pcap_flows_summary.csv")

    if not df.empty:
        print(f"Shape        : {df.shape}")
        print(f"Colonnes     : {list(df.columns)}")
        print(f"Protocoles   : {df['protocol'].value_counts().to_dict()}")
        print(f"Periode      : {df['timestamp'].min()} -> {df['timestamp'].max()}")
        print(df.head(3).to_string())

        taux = len(df) / 100000 * 100
        print(f"\nResultat     : {len(df):,}/100,000 flux parses ({taux:.0f}%)")
        print(f"CDC >= 90%   : {'OK' if taux >= 90 else 'KO'}")