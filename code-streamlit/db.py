import sqlite3
from typing import List, Optional
from regles import valider_reservation


def lister_salles(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Retourne la liste des salles triées par nom."""
    return conn.execute(
        "SELECT id, nom, capacite, projecteur FROM salles ORDER BY nom"
    ).fetchall()


def obtenir_salle(conn: sqlite3.Connection, salle_id: int) -> Optional[sqlite3.Row]:
    """Retourne une salle par son identifiant."""
    return conn.execute(
        "SELECT id, nom, capacite, projecteur FROM salles WHERE id = ?", [salle_id]
    ).fetchone()


def ajouter_salle(conn: sqlite3.Connection, nom: str, capacite: int, projecteur: bool) -> int:
    """Ajoute une nouvelle salle."""
    nom_propre = nom.strip()
    if not nom_propre:
        raise ValueError("Le nom de la salle ne peut pas être vide.")
    if capacite <= 0:
        raise ValueError("La capacité doit être supérieure à zéro.")

    cursor = conn.execute(
        "INSERT INTO salles (nom, capacite, projecteur) VALUES (?, ?, ?)",
        [nom_propre, int(capacite), 1 if projecteur else 0],
    )
    conn.commit()
    return cursor.lastrowid


def modifier_salle(
    conn: sqlite3.Connection, salle_id: int, nom: str, capacite: int, projecteur: bool
) -> None:
    """Modifie une salle existante."""
    nom_propre = nom.strip()
    if not nom_propre:
        raise ValueError("Le nom de la salle ne peut pas être vide.")
    if capacite <= 0:
        raise ValueError("La capacité doit être supérieure à zéro.")

    conn.execute(
        "UPDATE salles SET nom = ?, capacite = ?, projecteur = ? WHERE id = ?",
        [nom_propre, int(capacite), 1 if projecteur else 0, salle_id],
    )
    conn.commit()


def supprimer_salle(conn: sqlite3.Connection, salle_id: int) -> None:
    """Supprime une salle et ses réservations (ON DELETE CASCADE)."""
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM salles WHERE id = ?", [salle_id])
    conn.commit()


def lister_reservations(
    conn: sqlite3.Connection,
    salle_id: Optional[int] = None,
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
) -> List[sqlite3.Row]:
    """Retourne les réservations avec le nom de la salle, selon les filtres fournis."""
    requete = """
        SELECT r.id, r.salle_id, r.personne, r.date, r.debut, r.fin, r.participants,
               s.nom AS nom_salle, s.capacite AS capacite_salle, s.projecteur
        FROM reservations r
        JOIN salles s ON r.salle_id = s.id
        WHERE 1=1
    """
    params = []
    if salle_id is not None:
        requete += " AND r.salle_id = ?"
        params.append(salle_id)
    if date_debut is not None:
        requete += " AND r.date >= ?"
        params.append(date_debut)
    if date_fin is not None:
        requete += " AND r.date <= ?"
        params.append(date_fin)

    requete += " ORDER BY r.date, r.debut"
    return conn.execute(requete, params).fetchall()


def ajouter_reservation(
    conn: sqlite3.Connection,
    salle_id: int,
    personne: str,
    date_str: str,
    debut_str: str,
    fin_str: str,
    participants: int,
) -> int:
    """Valide et enregistre une nouvelle réservation."""
    personne_propre = personne.strip()
    if not personne_propre:
        raise ValueError("Le nom de la personne ne peut pas être vide.")

    salle = obtenir_salle(conn, salle_id)
    if not salle:
        raise ValueError("La salle sélectionnée n'existe pas.")

    # Récupérer les réservations existantes pour la même salle et même date
    existantes = conn.execute(
        "SELECT id, debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
        [salle_id, date_str],
    ).fetchall()
    existantes_dict = [dict(r) for r in existantes]

    valider_reservation(
        capacite_salle=salle["capacite"],
        participants=participants,
        debut=debut_str,
        fin=fin_str,
        reservations_existantes=existantes_dict,
    )

    cursor = conn.execute(
        """
        INSERT INTO reservations (salle_id, personne, date, debut, fin, participants)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [salle_id, personne_propre, date_str, debut_str, fin_str, int(participants)],
    )
    conn.commit()
    return cursor.lastrowid


def annuler_reservation(conn: sqlite3.Connection, reservation_id: int) -> None:
    """Supprime une réservation."""
    conn.execute("DELETE FROM reservations WHERE id = ?", [reservation_id])
    conn.commit()


def trouver_salles_libres(
    conn: sqlite3.Connection,
    date_str: str,
    debut_str: str,
    fin_str: str,
    participants: int,
    avec_projecteur: bool = False,
) -> List[sqlite3.Row]:
    """
    Trouve les salles disponibles pour un créneau, une capacité et une option projecteur.
    """
    toutes_salles = lister_salles(conn)
    salles_dispos = []

    for salle in toutes_salles:
        if salle["capacite"] < participants:
            continue
        if avec_projecteur and not salle["projecteur"]:
            continue

        # Vérifier s'il y a conflit
        existantes = conn.execute(
            "SELECT id, debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
            [salle["id"], date_str],
        ).fetchall()
        existantes_dict = [dict(r) for r in existantes]

        try:
            valider_reservation(
                capacite_salle=salle["capacite"],
                participants=participants,
                debut=debut_str,
                fin=fin_str,
                reservations_existantes=existantes_dict,
            )
            salles_dispos.append(salle)
        except ValueError:
            # Conflit d'horaires ou règle non respectée
            continue

    return salles_dispos

