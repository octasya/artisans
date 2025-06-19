# Artisans Discord Bot

Ce dépôt contient un bot Discord simplifié pour gérer un annuaire d'artisans uniquement à l'aide de boutons interactifs.

- `bot.py` : script principal du bot utilisant `discord.py`.
- `data.json` : fichier où sont conservées les inscriptions et les notes.

Remplacez `TOKEN` dans `bot.py` par le token de votre application Discord et `HOME_CHANNEL_ID` par l'identifiant du canal où le menu principal doit apparaître.

## Fonctionnalités principales

1. Inscription des artisans via une fenêtre modale (plusieurs métiers peuvent être listés séparés par des virgules).
2. Mise à jour de son profil depuis le menu principal.
3. Annuaire complet avec notes moyennes.
4. Recherche d'artisans par métier via un formulaire.
5. Classement des meilleurs artisans.
6. Bouton pour demander un devis. L'artisan envoie alors une offre que le client peut valider ou refuser.
7. Création d'un salon privé une fois le devis validé par le client, accessible uniquement aux deux membres et aux administrateurs.
8. Dans le salon privé, des boutons permettent de démarrer ou terminer la prestation puis de demander une note au client.
9. Système de notation de 1 à 5 étoiles.
10. Possibilité pour un artisan de se retirer de l'annuaire.
11. Sauvegarde automatique des inscriptions et des notes dans `data.json`.
12. Chaque note peut être accompagnée d'un commentaire.
13. Suivi du nombre de prestations réalisées par chaque artisan.
14. Consultation de son profil complet depuis le menu principal.
15. Statistiques globales et bouton pour les administrateurs afin d'envoyer une annonce à tous les artisans.
16. Dans chaque salon de prestation, un bouton permet d'appeler un modérateur en cas de litige.
17. Suivi de l'état de chaque commande (en attente, en cours, terminé ou litige) via des boutons dans le salon privé.
