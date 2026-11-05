from datetime import date

import pytest

from regles import (
    lundi_de_la_semaine,
    verifier_horaires_salle,
    verifier_reservation,
)

RESERVATIONS = [{"debut": "10:00", "fin": "12:00"}]


@pytest.mark.parametrize(
    "jour, attendu",
    [
        (date(2026, 11, 12), date(2026, 11, 9)),
        (date(2026, 11, 15), date(2026, 11, 9)),
    ],
)
def test_lundi_de_la_semaine(jour, attendu):
    assert lundi_de_la_semaine(jour) == attendu


@pytest.mark.parametrize(
    "debut, fin, participants, attendu",
    [
        ("11:00", "13:00", 5, "déjà réservée"),
        ("12:00", "13:00", 5, None),
        ("14:00", "15:00", 25, "participants"),
        ("07:30", "09:00", 5, "ouverte de 08:00"),
        ("14:00", "14:20", 5, "30 minutes"),
        ("08:00", "13:00", 5, "4 heures"),
        ("12:00", "11:00", 5, "se terminer"),
        ("14:00", "15:00", 0, "au moins 1"),
        ("14:00", "15:00", 20, None),
        ("08:00", "08:30", 5, None),
        ("14:00", "18:00", 5, None),
        ("16:00", "20:00", 5, None),
    ],
)
def test_verifier_reservation(debut, fin, participants, attendu):
    resultat = verifier_reservation(RESERVATIONS, 20, debut, fin, participants)

    if attendu is None:
        assert resultat is None
    else:
        assert attendu in resultat


@pytest.mark.parametrize(
    "debut, fin, attendu",
    [
        ("09:00", "10:00", None),
        ("16:00", "17:00", None),
        ("08:00", "09:00", "ouverte de 09:00 à 17:00"),
        ("08:30", "09:30", "ouverte de 09:00 à 17:00"),
        ("16:30", "17:30", "ouverte de 09:00 à 17:00"),
        ("18:00", "19:00", "ouverte de 09:00 à 17:00"),
    ],
)
def test_verifier_reservation_suit_les_horaires_de_la_salle(debut, fin, attendu):
    """Une salle ouverte de 9 h à 17 h refuse ce qui déborde, même entre 8 h et 20 h."""
    resultat = verifier_reservation(
        [], 20, debut, fin, 5, ouverture="09:00", fermeture="17:00"
    )

    if attendu is None:
        assert resultat is None
    else:
        assert attendu in resultat


@pytest.mark.parametrize(
    "ouverture, fermeture, attendu",
    [
        ("08:00", "20:00", None),
        ("09:00", "17:00", None),
        ("17:00", "09:00", "après son ouverture"),
        ("10:00", "10:00", "après son ouverture"),
        ("07:30", "17:00", "bâtiment est ouvert"),
        ("09:00", "20:30", "bâtiment est ouvert"),
        ("09:00", "09:15", "au moins 30 minutes"),
    ],
)
def test_verifier_horaires_salle(ouverture, fermeture, attendu):
    resultat = verifier_horaires_salle(ouverture, fermeture)

    if attendu is None:
        assert resultat is None
    else:
        assert attendu in resultat
