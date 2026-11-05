# NitroMP — Python Local Server v0.1

Prototype LAN du serveur multijoueur NitroMP pour BeamNG.drive.

## Prérequis

- Python 3.9 ou plus récent
- Deux ordinateurs sur le même réseau local pour tester à plusieurs

## Installation

Ouvre un terminal dans le dossier `server`, puis exécute :

```bash
python -m pip install -r requirements.txt
```

## Démarrage

```bash
python server.py
```

Le serveur affiche deux adresses :
- `ws://127.0.0.1:8765` pour tester sur le même ordinateur
- `ws://ADRESSE_LAN:8765` pour les autres ordinateurs du réseau

Sur le deuxième ordinateur, utilise l'adresse LAN affichée sur le PC hôte.

Si macOS ou Windows demande l'autorisation du pare-feu, autorise Python sur le réseau privé/local.

## Test rapide sans BeamNG

Avec le serveur lancé, ouvre un deuxième terminal et installe aussi `websockets==12.0`.
Puis lance le client de test :

```bash
python test_client.py ws://127.0.0.1:8765 Joueur1 salon-1
```

Tu peux lancer une deuxième instance avec un autre nom pour voir les messages de présence.

## Sécurité

Cette version est conçue pour le réseau local uniquement. Elle ne possède ni authentification ni chiffrement.
Ne configure pas de redirection de port sur ta box et ne l'expose pas à Internet.

## État du projet

v0.1 = serveur WebSocket, salons, présence des joueurs et relais de données véhicule.
Le mod BeamNG Lua n'est pas encore connecté : les coordonnées de véhicule sont pour le moment des données de test.
