import sqlite3
from pathlib import Path
import pytest
from db import (
    lister_salles,
    obtenir_salle,
    ajouter_salle,
    modifier_salle,
    supprimer_salle,
    lister_reservations,
    ajouter_reservation,
    annuler_reservation,
    trouver_salles_libres,
)


@pytest.fixture
def conn():
    """Crée une base SQLite en mémoire avec le schéma initial."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    schema = (Path(__file__).parent.parent / "base.sql").read_text(encoding="utf-8")
    c.executescript(schema)
    return c


def test_gestion_salles(conn):
    # Lister les salles initiales (S1, S2)
    salles = lister_salles(conn)
    assert len(salles) == 2
    noms = [s["nom"] for s in salles]
    assert "S1" in noms
    assert "S2" in noms

    # Ajouter une salle S3
    s3_id = ajouter_salle(conn, "S3", 15, True)
    assert s3_id is not None
    s3 = obtenir_salle(conn, s3_id)
    assert s3["nom"] == "S3"
    assert s3["capacite"] == 15
    assert s3["projecteur"] == 1

    # Modifier S3
    modifier_salle(conn, s3_id, "S3-Renommee", 18, False)
    s3_mod = obtenir_salle(conn, s3_id)
    assert s3_mod["nom"] == "S3-Renommee"
    assert s3_mod["capacite"] == 18
    assert s3_mod["projecteur"] == 0

    # Supprimer S3
    supprimer_salle(conn, s3_id)
    assert obtenir_salle(conn, s3_id) is None


def test_suppression_salle_en_cascade(conn):
    # S1 a des réservations dans base.sql
    res_avant = lister_reservations(conn, salle_id=1)
    assert len(res_avant) >= 1

    # Supprimer la salle S1 doit supprimer toutes ses réservations (ON DELETE CASCADE)
    supprimer_salle(conn, 1)
    salle_1 = obtenir_salle(conn, 1)
    assert salle_1 is None

    res_apres = conn.execute("SELECT * FROM reservations WHERE salle_id = 1").fetchall()
    assert len(res_apres) == 0


def test_ajouter_et_annuler_reservation(conn):
    # S1 a une réservation le lundi 2026-11-09 de 10:00 à 12:00
    # Ajouter une réservation valide de 12:00 à 13:00 pour 10 participants
    res_id = ajouter_reservation(
        conn,
        salle_id=1,
        personne="Bob",
        date_str="2026-11-09",
        debut_str="12:00",
        fin_str="13:00",
        participants=10,
    )
    assert res_id is not None

    # Lister les réservations de S1 le 2026-11-09
    res = lister_reservations(conn, salle_id=1, date_debut="2026-11-09", date_fin="2026-11-09")
    assert len(res) == 2

    # Annuler la réservation de Bob
    annuler_reservation(conn, res_id)
    res_apres = lister_reservations(conn, salle_id=1, date_debut="2026-11-09", date_fin="2026-11-09")
    assert len(res_apres) == 1


def test_ajouter_reservation_chevauchement_refuse(conn):
    # S1 déjà réservée 10:00 - 12:00
    with pytest.raises(ValueError, match="chevauche"):
        ajouter_reservation(
            conn,
            salle_id=1,
            personne="Charlie",
            date_str="2026-11-09",
            debut_str="11:00",
            fin_str="13:00",
            participants=5,
        )


def test_trouver_salles_libres(conn):
    # Le lundi 2026-11-09 :
    # S1 (capacité 20, projecteur 1) est occupée de 10h à 12h
    # S2 (capacité 8, projecteur 0) est libre toute la journée

    # Chercher pour 10:30 - 11:30, 5 personnes, sans projecteur
    # S1 est occupée, S2 a capacité 8 >= 5 -> seule S2 doit être libre
    libres = trouver_salles_libres(
        conn,
        date_str="2026-11-09",
        debut_str="10:30",
        fin_str="11:30",
        participants=5,
        avec_projecteur=False,
    )
    assert len(libres) == 1
    assert libres[0]["nom"] == "S2"

    # Chercher pour 12:00 - 14:00, 15 personnes
    # S1 a capacité 20 >= 15 et est libre à 12:00
    # S2 a capacité 8 < 15
    libres_15 = trouver_salles_libres(
        conn,
        date_str="2026-11-09",
        debut_str="12:00",
        fin_str="14:00",
        participants=15,
        avec_projecteur=False,
    )
    assert len(libres_15) == 1
    assert libres_15[0]["nom"] == "S1"

    # Chercher avec projecteur requis
    libres_proj = trouver_salles_libres(
        conn,
        date_str="2026-11-09",
        debut_str="12:00",
        fin_str="14:00",
        participants=5,
        avec_projecteur=True,
    )
    assert len(libres_proj) == 1
    assert libres_proj[0]["nom"] == "S1"

