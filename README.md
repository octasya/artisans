# Artisans Discord Bot

Ce dépôt contient un bot Discord simplifié pour gérer un annuaire d'artisans uniquement à l'aide de boutons interactifs.

- `bot.py` : script principal du bot utilisant `discord.py`.

Remplacez `TOKEN` dans `bot.py` par le token de votre application Discord et `HOME_CHANNEL_ID` par l'identifiant du canal où le menu principal doit apparaître.

## Fonctionnalités principales

1. Inscription des artisans via une fenêtre modale.
2. Mise à jour de son profil depuis le menu principal.
3. Annuaire complet avec notes moyennes.
4. Recherche d'artisans par métier via un formulaire.
5. Classement des meilleurs artisans.
6. Bouton pour demander un devis. L'artisan envoie alors une offre que le client peut valider ou refuser.
7. Création d'un salon privé une fois le devis validé par le client, accessible uniquement aux deux membres et aux administrateurs.
8. Bouton "Terminer" dans le salon pour clore la prestation et demander une note au client.
9. Système de notation de 1 à 5 étoiles.
10. Possibilité pour un artisan de se retirer de l'annuaire.
