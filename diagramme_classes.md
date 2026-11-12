# Diagramme de classes - Réservation de salles

Ce document présente l'architecture logicielle et le diagramme de classes du système de réservation de salles (Streamlit, SQLite, Python).

```mermaid
classDiagram
    direction TB

    class Salle {
        +int id
        +str nom
        +int capacite
        +bool projecteur
        +str type
    }

    class Reservation {
        +int id
        +int salle_id
        +str personne
        +str date
        +str debut
        +str fin
        +int participants
        +str recurrence_id
    }

    class ReglesMetier {
        <<module regles.py>>
        +heure_en_minutes(h) int
        +minutes_en_heure(m) str
        +valider_horaires(debut, fin) tuple
        +valider_capacite(participants, capacite) void
        +valider_type_salle(type_salle) str
        +sont_en_chevauchement(d1, f1, d2, f2) bool
        +valider_non_chevauchement_personne(personne, debut, fin, reservations) void
        +valider_reservation(capacite, participants, debut, fin, existantes, personne, ...) void
        +generer_dates_recurrence(date_debut, nb_semaines) list
        +obtenir_semaine(date_ref) tuple
        +calculer_taux_occupation(reservations) float
    }

    class GestionnaireDonnees {
        <<module db.py>>
        +lister_salles(conn) list
        +obtenir_salle(conn, salle_id) Row
        +ajouter_salle(conn, nom, capacite, projecteur, type_salle) int
        +modifier_salle(conn, salle_id, nom, capacite, projecteur, type_salle) void
        +supprimer_salle(conn, salle_id) void
        +lister_reservations(conn, salle_id, date_debut, date_fin, personne, recurrence_id) list
        +ajouter_reservation(conn, salle_id, personne, date_str, debut, fin, participants, nb_semaines) int
        +annuler_reservation(conn, reservation_id) void
        +annuler_recurrence(conn, recurrence_id) void
        +trouver_salles_libres(conn, date_str, debut, fin, participants, avec_projecteur, type_salle, personne) list
    }

    class ApplicationStreamlit {
        <<module app.py>>
        +tab_planning()
        +tab_reserver()
        +tab_annuler()
        +tab_salles()
        +tab_recherche()
    }

    Salle "1" *-- "0..*" Reservation : ON DELETE CASCADE
    GestionnaireDonnees ..> Salle : persiste et lit
    GestionnaireDonnees ..> Reservation : persiste et lit
    GestionnaireDonnees ..> ReglesMetier : valide avant insertion
    ApplicationStreamlit ..> GestionnaireDonnees : requêtes CRUD
    ApplicationStreamlit ..> ReglesMetier : calculs calendrier et taux
```

---

## Description des composants

1. **Entités de données (`Salle`, `Reservation`)** :
   - `Salle` représente un local avec son nom, sa capacité maximale, la présence ou non d'un projecteur, ainsi que son `type` (ex. *Salle de cours*, *Salle de réunion*, *Amphithéâtre*, etc.).
   - `Reservation` associe une salle à une personne sur une date et une plage horaire donnée (`debut` - `fin`), avec un nombre de participants. Si la réservation est hebdomadaire, elle partage un `recurrence_id` commun avec ses occurrences sœurs.
   - La relation entre `Salle` et `Reservation` est une composition avec contrainte d'intégrité référentielle `ON DELETE CASCADE` : la suppression d'une salle entraîne automatiquement la suppression de ses réservations.

2. **Règles métier pures (`regles.py`)** :
   - Fonctions pures indépendantes de la base de données et du framework d'affichage.
   - Contrôle la plage horaire (8 h - 20 h) et la durée autorisée (30 min - 4 h).
   - Contrôle le non-dépassement de la capacité.
   - Empêche les chevauchements temporels pour une même salle.
   - Empêche les chevauchements pour une même personne (une personne ne peut pas avoir deux réservations en même temps).
   - Valide le type de local et calcule les récurrences hebdomadaires, les bornes de la semaine (lundi au dimanche) et le taux d'occupation.

3. **Couche d'accès aux données (`db.py`)** :
   - Centralise l'ensemble des requêtes SQL et transactions SQLite.
   - Valide les règles métier avant toute écriture.
   - Garantit l'atomicité lors de la réservation de séries récurrentes.

4. **Interface utilisateur Streamlit (`app.py`)** :
   - Coordonne les 5 vues principales : planning hebdomadaire avec export CSV, formulaire de réservation (unique ou récurrente), annulation unitaire ou par série, gestion du parc de salles et recherche multicritère de salles libres.
