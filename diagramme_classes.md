# Diagramme de classes - Réservation de salles

Ce document présente le diagramme de classes du système de réservation de salles après nos ajouts (contrainte par personne, type de local, réservations répétées chaque semaine), puis l'architecture du code (Streamlit, SQLite, Python).

## 1. Diagramme de classes (modèle du domaine)

```mermaid
classDiagram
    direction LR

    class Salle {
        +nom: str
        +capacite: int
        +projecteur: bool
    }

    class TypeLocal {
        <<enumeration>>
        SALLE_DE_COURS
        SALLE_DE_REUNION
        AMPHITHEATRE
        SALLE_INFORMATIQUE
        LABORATOIRE
    }

    class Reservation {
        +date: Date
        +debut: Time
        +fin: Time
        +participants: int
    }

    class Personne {
        +nom: str
    }

    class SerieHebdomadaire {
        +nbSemaines: int
    }

    Salle "1" *-- "0..*" Reservation : accueille
    Salle "0..*" --> "1" TypeLocal : est de type
    Personne "1" -- "0..*" Reservation : réserve
    SerieHebdomadaire "0..1" o-- "1..*" Reservation : regroupe

    note for Reservation "Entre 8 h et 20 h, durée de 30 min à 4 h.\nparticipants ≤ capacité de la salle.\nPas de chevauchement dans une même salle.\nPas de chevauchement pour une même personne."
```

### Lecture du diagramme

- **Salle — Reservation** : composition. Supprimer une salle supprime ses réservations (`ON DELETE CASCADE` dans `base.sql`).
- **TypeLocal** (ajout B2) : chaque salle a exactement un type, choisi dans une liste fixe (`TYPES_SALLES_DEFAUT` dans `regles.py`).
- **Personne** (ajout B1) : une personne peut avoir plusieurs réservations, mais jamais deux qui se chevauchent, toutes salles confondues.
- **SerieHebdomadaire** (ajout B3) : une réservation répétée chaque semaine crée une série d'occurrences, qui peuvent être annulées ensemble. Une réservation simple n'appartient à aucune série.

### Correspondance avec la base de données

Le diagramme est conceptuel : toutes les classes n'ont pas leur propre table.

| Classe | Dans la base |
|---|---|
| `Salle` | table `salles` |
| `TypeLocal` | colonne `salles.type` (texte) |
| `Reservation` | table `reservations` |
| `Personne` | colonne `reservations.personne` (texte, comparé sans tenir compte de la casse ni des espaces) |
| `SerieHebdomadaire` | colonne `reservations.recurrence_id`, commune à toutes les occurrences d'une série |

Comme il n'y a pas d'authentification, une personne est identifiée uniquement par son nom.

## 2. Architecture du code

Le code n'est pas orienté objet : il est organisé en trois modules de fonctions. Le schéma ci-dessous montre ces modules et leurs dépendances, pas des classes.

```mermaid
classDiagram
    direction TB

    class app {
        <<module app.py>>
        Onglet Planning
        Onglet Réserver
        Onglet Annuler
        Onglet Salles
        Onglet Recherche
    }

    class db {
        <<module db.py>>
        +lister_salles(conn) list
        +obtenir_salle(conn, salle_id) Row
        +ajouter_salle(conn, nom, capacite, projecteur, type_salle) int
        +modifier_salle(conn, salle_id, nom, capacite, projecteur, type_salle) None
        +supprimer_salle(conn, salle_id) None
        +lister_reservations(conn, salle_id, date_debut, date_fin, personne, recurrence_id) list
        +ajouter_reservation(conn, salle_id, personne, date_str, debut, fin, participants, nb_semaines) int
        +annuler_reservation(conn, reservation_id) None
        +annuler_recurrence(conn, recurrence_id) None
        +trouver_salles_libres(conn, date_str, debut, fin, participants, avec_projecteur, type_salle, personne) list
    }

    class regles {
        <<module regles.py>>
        +heure_en_minutes(h) int
        +minutes_en_heure(m) str
        +valider_horaires(debut, fin) tuple
        +valider_capacite(participants, capacite) None
        +valider_type_salle(type_salle) str
        +sont_en_chevauchement(d1, f1, d2, f2) bool
        +valider_non_chevauchement_personne(personne, debut, fin, reservations_personne, reservation_id_ignore) None
        +valider_reservation(capacite_salle, participants, debut, fin, reservations_existantes, personne, reservations_personne, reservation_id_ignore) None
        +generer_dates_recurrence(date_debut, nb_semaines) list
        +obtenir_semaine(date_ref) tuple
        +calculer_taux_occupation(reservations) float
    }

    app ..> db : lit et écrit les données
    app ..> regles : calendrier et taux d'occupation
    db ..> regles : valide avant d'écrire
```

### Description des modules

1. **Règles métier (`regles.py`)** : fonctions pures, indépendantes de la base et de Streamlit, donc faciles à tester. Elles contrôlent la plage horaire (8 h - 20 h), la durée (30 min - 4 h), la capacité, les chevauchements par salle et par personne, le type de local, et calculent les dates d'une série hebdomadaire, les bornes de la semaine et le taux d'occupation.

2. **Accès aux données (`db.py`)** : contient toutes les requêtes SQL. Chaque écriture passe d'abord par les règles métier. Pour une série hebdomadaire, toutes les occurrences sont validées avant la première insertion : si une seule est refusée, rien n'est enregistré.

3. **Interface (`app.py`)** : cinq onglets Streamlit — planning hebdomadaire avec export CSV, réservation (simple ou répétée), annulation (une réservation ou toute une série), gestion des salles et recherche d'une salle libre.
