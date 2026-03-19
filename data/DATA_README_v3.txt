# Jeu de données fictif – NOC‑Edge FTTH (Version v3 – MAX)

Ce paquet contient des **données entièrement synthétiques** pour un projet FTTH/GPON offline.
- Période : 30 jours, résolution 5 min
- ONT : 100 (ONT_101 .. ONT_200)
- Flux PCAP simulés : 100 000 lignes
- Événements sécurité : 500

## Dossiers
- csv/ : KPIs, QoS, ONT, budget optique, sécurité, topologie
- snmp/ : snapshots SNMP fictifs (OLT + 100 ONT)
- traces/ : résumé de flux PCAP simulés

## Notes
- Fenêtres d’anomalies injectées dans KPI & QoS pour tests IA
- Scénarios optiques incluent 1:128 et 1:256 (long distance)
- Toutes les valeurs/OIDs sont inventés, usage pédagogique uniquement
