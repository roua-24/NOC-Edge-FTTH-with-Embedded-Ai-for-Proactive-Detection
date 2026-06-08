"""
Module : RAPPORTS — pdf_generator.py
Rôle   : Génération de rapports PDF (KPI, anomalies, conformité sécurité)
Entrée : df_kpi, rapport_conformite, figures matplotlib
Sortie : fichier .pdf dans reports/
"""
# TODO S12 : implémenter avec reportlab
# from reportlab.lib.pagesizes import A4
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table
# from io import BytesIO

def generate_pdf(df_kpi, rapport_conformite: dict, figures: list,
                 output_path: str = "reports/rapport_noc.pdf") -> str:
    """
    Génère un rapport PDF complet.

    Returns
    -------
    str — chemin du fichier PDF généré
    """
    raise NotImplementedError("PDF generator — implémentation prévue en S12")
