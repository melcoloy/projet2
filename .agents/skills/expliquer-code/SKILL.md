---
name: expliquer-code
description: Explique les derniers changements : résumé en 5 lignes, diagramme de séquence et flowchart. À utiliser quand on demande d'expliquer, de documenter ou de relire ce qui vient d'être modifié.
---

# Expliquer le code

## Étapes

1. Lis `git diff`. S'il est vide, lis `git diff HEAD~1` et dis lequel tu as utilisé.
2. Écris un résumé de 5 lignes maximum : ce qui change et pourquoi, pas comment.
3. Dessine un diagramme de séquence Mermaid de l'utilisateur jusqu'à la base.
4. Dessine un flowchart Mermaid des décisions prises par le code (les refus, les cas d'erreur).
5. Ne modifie aucun fichier.

## Forme

````markdown
## Résumé
5 lignes maximum.

## Séquence
```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant A as app.py
    participant R as regles.py
    participant B as data.db
    U->>A: remplit le formulaire
    A->>B: lit les réservations du jour
    A->>R: verifier_reservation(...)
    R-->>A: None ou message de refus
    A->>B: INSERT si accepté
    A-->>U: succès ou message de refus
```

## Décisions
```mermaid
flowchart TD
    A[Demande] --> B{Entre 8 h et 20 h ?}
    B -- non --> R[Refus]
    B -- oui --> C{Durée 30 min à 4 h ?}
    C -- non --> R
    C -- oui --> D{Participants <= capacité ?}
    D -- non --> R
    D -- oui --> E{Chevauchement ?}
    E -- oui --> R
    E -- non --> F[Enregistrée]
```
````

## Interdit

- Modifier des fichiers.
- Inventer un comportement qui n'est pas dans le diff.
- Dépasser 5 lignes de résumé.
