import sqlite3
import uuid
from datetime import date
from typing import List, Optional, Union
from regles import (
    generer_dates_recurrence,
    valider_reservation,
    valider_type_salle,
)


def lister_salles(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Retourne la liste des salles triées par nom."""
    return conn.execute(
        "SELECT id, nom, capacite, projecteur, type FROM salles ORDER BY nom"
    ).fetchall()


def obtenir_salle(conn: sqlite3.Connection, salle_id: int) -> Optional[sqlite3.Row]:
    """Retourne une salle par son identifiant."""
    return conn.execute(
        "SELECT id, nom, capacite, projecteur, type FROM salles WHERE id = ?", [salle_id]
    ).fetchone()


def ajouter_salle(
    conn: sqlite3.Connection,
    nom: str,
    capacite: int,
    projecteur: bool,
    type_salle: str = "Salle de cours",
) -> int:
    """Ajoute une nouvelle salle avec son type."""
    nom_propre = nom.strip()
    if not nom_propre:
        raise ValueError("Le nom de la salle ne peut pas être vide.")
    if capacite <= 0:
        raise ValueError("La capacité doit être supérieure à zéro.")
    type_propre = valider_type_salle(type_salle)

    cursor = conn.execute(
        "INSERT INTO salles (nom, capacite, projecteur, type) VALUES (?, ?, ?, ?)",
        [nom_propre, int(capacite), 1 if projecteur else 0, type_propre],
    )
    conn.commit()
    return cursor.lastrowid


def modifier_salle(
    conn: sqlite3.Connection,
    salle_id: int,
    nom: str,
    capacite: int,
    projecteur: bool,
    type_salle: str = "Salle de cours",
) -> None:
    """Modifie une salle existante, y compris son type."""
    nom_propre = nom.strip()
    if not nom_propre:
        raise ValueError("Le nom de la salle ne peut pas être vide.")
    if capacite <= 0:
        raise ValueError("La capacité doit être supérieure à zéro.")
    type_propre = valider_type_salle(type_salle)

    conn.execute(
        "UPDATE salles SET nom = ?, capacite = ?, projecteur = ?, type = ? WHERE id = ?",
        [nom_propre, int(capacite), 1 if projecteur else 0, type_propre, salle_id],
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
    personne: Optional[str] = None,
    recurrence_id: Optional[str] = None,
) -> List[sqlite3.Row]:
    """Retourne les réservations avec le nom et le type de salle, selon les filtres fournis."""
    requete = """
        SELECT r.id, r.salle_id, r.personne, r.date, r.debut, r.fin, r.participants,
               r.recurrence_id, s.nom AS nom_salle, s.capacite AS capacite_salle,
               s.projecteur, s.type AS type_salle
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
    if personne is not None:
        requete += " AND LOWER(TRIM(r.personne)) = LOWER(TRIM(?))"
        params.append(personne)
    if recurrence_id is not None:
        requete += " AND r.recurrence_id = ?"
        params.append(recurrence_id)

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
    nb_semaines: int = 1,
) -> int:
    """
    Valide et enregistre une ou plusieurs réservations (récurrence hebdomadaire).
    Vérifie le non-chevauchement de la salle ET de la personne.
    Toutes les occurrences sont validées au préalable avant insertion.
    """
    personne_propre = personne.strip()
    if not personne_propre:
        raise ValueError("Le nom de la personne ne peut pas être vide.")

    salle = obtenir_salle(conn, salle_id)
    if not salle:
        raise ValueError("La salle sélectionnée n'existe pas.")

    dates = generer_dates_recurrence(date_str, nb_semaines)

    # 1. Pré-validation de chaque date pour garantir l'atomicité
    for d in dates:
        d_str = d.strftime("%Y-%m-%d")

        # Réservations de la même salle ce jour-là
        existantes_salle = conn.execute(
            "SELECT id, debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
            [salle_id, d_str],
        ).fetchall()
        existantes_salle_dict = [dict(r) for r in existantes_salle]

        # Réservations de la même personne ce jour-là (toutes salles confondues)
        existantes_personne = conn.execute(
            """
            SELECT r.id, r.salle_id, r.personne, r.debut, r.fin, s.nom AS nom_salle
            FROM reservations r
            JOIN salles s ON r.salle_id = s.id
            WHERE r.date = ? AND LOWER(TRIM(r.personne)) = LOWER(TRIM(?))
            """,
            [d_str, personne_propre],
        ).fetchall()
        existantes_personne_dict = [dict(r) for r in existantes_personne]

        try:
            valider_reservation(
                capacite_salle=salle["capacite"],
                participants=participants,
                debut=debut_str,
                fin=fin_str,
                reservations_existantes=existantes_salle_dict,
                personne=personne_propre,
                reservations_personne=existantes_personne_dict,
            )
        except ValueError as err:
            if nb_semaines > 1:
                raise ValueError(f"Conflit le {d_str} : {err}")
            raise err

    # 2. Insertion
    recurrence_id = uuid.uuid4().hex[:8] if nb_semaines > 1 else None
    premier_id = None

    for d in dates:
        d_str = d.strftime("%Y-%m-%d")
        cursor = conn.execute(
            """
            INSERT INTO reservations (salle_id, personne, date, debut, fin, participants, recurrence_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [salle_id, personne_propre, d_str, debut_str, fin_str, int(participants), recurrence_id],
        )
        if premier_id is None:
            premier_id = cursor.lastrowid

    conn.commit()
    return premier_id


def annuler_reservation(conn: sqlite3.Connection, reservation_id: int) -> None:
    """Supprime une réservation unique."""
    conn.execute("DELETE FROM reservations WHERE id = ?", [reservation_id])
    conn.commit()


def annuler_recurrence(conn: sqlite3.Connection, recurrence_id: str) -> None:
    """Supprime toutes les réservations d'une série récurrente."""
    conn.execute("DELETE FROM reservations WHERE recurrence_id = ?", [recurrence_id])
    conn.commit()


def trouver_salles_libres(
    conn: sqlite3.Connection,
    date_str: str,
    debut_str: str,
    fin_str: str,
    participants: int,
    avec_projecteur: bool = False,
    type_salle: Optional[str] = None,
    personne: Optional[str] = None,
) -> List[sqlite3.Row]:
    """
    Trouve les salles disponibles pour un créneau, une capacité, un type et une option projecteur.
    Optionnellement vérifie également que la personne n'a pas déjà un conflit sur ce créneau.
    """
    toutes_salles = lister_salles(conn)
    salles_dispos = []

    # Vérification éventuelle de la disponibilité de la personne
    existantes_personne_dict = []
    if personne and personne.strip():
        existantes_personne = conn.execute(
            """
            SELECT r.id, r.salle_id, r.personne, r.debut, r.fin, s.nom AS nom_salle
            FROM reservations r
            JOIN salles s ON r.salle_id = s.id
            WHERE r.date = ? AND LOWER(TRIM(r.personne)) = LOWER(TRIM(?))
            """,
            [date_str, personne.strip()],
        ).fetchall()
        existantes_personne_dict = [dict(r) for r in existantes_personne]

    for salle in toutes_salles:
        if salle["capacite"] < participants:
            continue
        if avec_projecteur and not salle["projecteur"]:
            continue
        if type_salle and salle["type"].strip().lower() != type_salle.strip().lower():
            continue

        # Vérifier conflit salle
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
                personne=personne.strip() if personne else None,
                reservations_personne=existantes_personne_dict,
            )
            salles_dispos.append(salle)
        except ValueError:
            continue

    return salles_dispos
