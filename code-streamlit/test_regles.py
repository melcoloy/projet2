import pytest

from regles import verifier_reservation

RESERVATIONS = [{"debut": "10:00", "fin": "12:00"}]


@pytest.mark.parametrize(
    "debut, fin, participants, attendu",
    [
        ("11:00", "13:00", 5, "déjà réservée"),
        ("12:00", "13:00", 5, None),
        ("14:00", "15:00", 25, "participants"),
        ("07:30", "09:00", 5, "8 h"),
        ("14:00", "14:20", 5, "30 minutes"),
        ("08:00", "13:00", 5, "4 heures"),
    ],
)
def test_verifier_reservation(debut, fin, participants, attendu):
    resultat = verifier_reservation(RESERVATIONS, 20, debut, fin, participants)

    if attendu is None:
        assert resultat is None
    else:
        assert attendu in resultat
