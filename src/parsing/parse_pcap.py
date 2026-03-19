"""
Module : PARSING — parse_pcap.py
Rôle   : Lire les fichiers .pcap synthétiques et extraire les flux réseau
Entrée : chemin vers un fichier .pcap (str | Path)
Sortie : pandas.DataFrame avec colonnes normalisées

Colonnes produites :
    timestamp  (datetime64)  — horodatage du paquet
    src_ip     (str)          — adresse IP source
    dst_ip     (str)          — adresse IP destination
    protocol   (str)          — TCP / UDP / ICMP / ARP / DHCP
    src_port   (int)          — port source (0 si non applicable)
    dst_port   (int)          — port destination (0 si non applicable)
    length     (int)          — taille du paquet en octets
    direction  (str)          — 'rx' ou 'tx' (à déduire selon l'OLT ref)
"""

import pandas as pd
from pathlib import Path


# ── Constantes ──────────────────────────────────────────────────────────────
PROTO_MAP = {1: "ICMP", 6: "TCP", 17: "UDP"}
OLT_MGMT_IP = "192.168.100.1"   # IP de référence OLT (fictive)


def parse_pcap(filepath: str | Path) -> pd.DataFrame:
    """
    Lit un fichier .pcap et retourne un DataFrame normalisé.

    Parameters
    ----------
    filepath : str | Path
        Chemin vers le fichier .pcap à parser.

    Returns
    -------
    pd.DataFrame
        DataFrame avec les colonnes : timestamp, src_ip, dst_ip,
        protocol, src_port, dst_port, length, direction.

    Raises
    ------
    FileNotFoundError
        Si le fichier n'existe pas.
    ValueError
        Si le fichier n'est pas un .pcap valide.
    """
    # TODO S3 : implémenter avec Scapy
    # from scapy.all import rdpcap, IP, TCP, UDP, ICMP
    # packets = rdpcap(str(filepath))
    # rows = []
    # for pkt in packets:
    #     if IP not in pkt:
    #         continue
    #     row = {
    #         "timestamp": pd.Timestamp(pkt.time, unit="s"),
    #         "src_ip":    pkt[IP].src,
    #         "dst_ip":    pkt[IP].dst,
    #         "protocol":  PROTO_MAP.get(pkt[IP].proto, str(pkt[IP].proto)),
    #         "src_port":  pkt[TCP].sport if TCP in pkt else (pkt[UDP].sport if UDP in pkt else 0),
    #         "dst_port":  pkt[TCP].dport if TCP in pkt else (pkt[UDP].dport if UDP in pkt else 0),
    #         "length":    len(pkt),
    #         "direction": "tx" if pkt[IP].src == OLT_MGMT_IP else "rx",
    #     }
    #     rows.append(row)
    # return pd.DataFrame(rows)
    raise NotImplementedError("parse_pcap — implémentation prévue en S3")


def get_protocol_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne un DataFrame de statistiques par protocole (count, bytes_total)."""
    # TODO S3
    raise NotImplementedError
