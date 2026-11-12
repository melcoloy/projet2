from datetime import date, time
import pytest
from regles import (
    valider_horaires,
    valider_capacite,
    valider_type_salle,
    sont_en_chevauchement,
    valider_non_chevauchement_personne,
    valider_reservation,
    generer_dates_recurrence,
    obtenir_semaine,
    calculer_taux_occupation,
)


def test_valider_horaires_valide():
    debut, fin, duree = valider_horaires("08:00", "12:00")
    assert debut == 480
    assert fin == 720
    assert duree == 240


def test_valider_horaires_avant_8h():
    # Lundi, 7 h 30 à 9 h : Refusée (avant 8 h)
    with pytest.raises(ValueError, match="avant 8 h"):
        valider_horaires("07:30", "09:00")


def test_valider_horaires_apres_20h():
    with pytest.raises(ValueError, match="après 20 h"):
        valider_horaires("18:00", "20:30")


def test_valider_horaires_moins_de_30_min():
    # Mardi, 14 h à 14 h 20 : Refusée (moins de 30 min)
    with pytest.raises(ValueError, match="au moins 30 minutes"):
        valider_horaires("14:00", "14:20")


def test_valider_horaires_plus_de_4h():
    # Mardi, 8 h à 13 h : Refusée (plus de 4 h)
    with pytest.raises(ValueError, match="dépasser 4 heures"):
        valider_horaires("08:00", "13:00")


def test_valider_horaires_fin_avant_debut():
    with pytest.raises(ValueError, match="postérieure"):
        valider_horaires("15:00", "14:00")


def test_valider_capacite():
    # Capacité 20, 20 participants -> OK
    valider_capacite(20, 20)

    # Capacité 20, 25 participants -> Refusée : capacité dépassée
    with pytest.raises(ValueError, match="dépasse la capacité"):
        valider_capacite(25, 20)

    # 0 participant -> Refusé
    with pytest.raises(ValueError, match="supérieur à zéro"):
        valider_capacite(0, 20)


def test_valider_type_salle():
    assert valider_type_salle("Salle de cours") == "Salle de cours"
    assert valider_type_salle("  Amphithéâtre  ") == "Amphithéâtre"

    with pytest.raises(ValueError, match="ne peut pas être vide"):
        valider_type_salle("")
    with pytest.raises(ValueError, match="ne peut pas être vide"):
        valider_type_salle("   ")


def test_chevauchement():
    # Déjà réservé de 10:00 à 12:00
    # 1. 11h à 13h -> Refusée (chevauchement)
    assert sont_en_chevauchement("10:00", "12:00", "11:00", "13:00") is True

    # 2. 12h à 13h -> Acceptée (finir à 12h et commencer à 12h autorisé)
    assert sont_en_chevauchement("10:00", "12:00", "12:00", "13:00") is False

    # 3. 09h à 10h -> Acceptée
    assert sont_en_chevauchement("10:00", "12:00", "09:00", "10:00") is False

    # 4. Inclus à l'intérieur : 10:30 à 11:30
    assert sont_en_chevauchement("10:00", "12:00", "10:30", "11:30") is True


def test_non_chevauchement_personne():
    # Alice a déjà une réservation dans S1 de 10h à 12h
    res_personnes = [
        {"id": 1, "salle_id": 1, "nom_salle": "S1", "personne": "Alice", "debut": "10:00", "fin": "12:00"}
    ]

    # Alice veut réserver S2 de 11h à 13h -> Refusé : elle est déjà occupée
    with pytest.raises(ValueError, match="Alice a déjà une réservation sur ce créneau"):
        valider_non_chevauchement_personne("Alice", "11:00", "13:00", res_personnes)

    # Insensible à la casse / espaces
    with pytest.raises(ValueError, match="alice a déjà une réservation"):
        valider_non_chevauchement_personne("  alice ", "10:30", "11:30", res_personnes)

    # Alice réserve S2 de 12h à 13h -> Accepté (finir à 12h et commencer à 12h)
    valider_non_chevauchement_personne("Alice", "12:00", "13:00", res_personnes)

    # Bob peut réserver S2 de 10h à 12h -> Accepté (autre personne)
    valider_non_chevauchement_personne("Bob", "10:00", "12:00", res_personnes)


def test_generer_dates_recurrence():
    dates = generer_dates_recurrence("2026-11-09", 4)
    assert len(dates) == 4
    assert dates[0] == date(2026, 11, 9)
    assert dates[1] == date(2026, 11, 16)
    assert dates[2] == date(2026, 11, 23)
    assert dates[3] == date(2026, 11, 30)

    with pytest.raises(ValueError, match="au moins de 1"):
        generer_dates_recurrence("2026-11-09", 0)


def test_cas_du_readme():
    """Vérifie le tableau 'Pour vérifier' du README avec salle S1 (capacité 20, réservée lundi 10h-12h)."""
    salle_capacite = 20
    reservations_existantes = [
        {"id": 1, "salle_id": 1, "debut": "10:00", "fin": "12:00", "participants": 12}
    ]

    # Lundi, 11 h à 13 h -> Refusée : chevauchement
    with pytest.raises(ValueError, match="chevauche"):
        valider_reservation(salle_capacite, 10, "11:00", "13:00", reservations_existantes)

    # Lundi, 12 h à 13 h -> Acceptée
    valider_reservation(salle_capacite, 10, "12:00", "13:00", reservations_existantes)

    # Lundi, 14 h à 15 h, 25 participants -> Refusée : capacité dépassée
    with pytest.raises(ValueError, match="dépasse la capacité"):
        valider_reservation(salle_capacite, 25, "14:00", "15:00", reservations_existantes)

    # Lundi, 7 h 30 à 9 h -> Refusée : avant 8 h
    with pytest.raises(ValueError, match="avant 8 h"):
        valider_reservation(salle_capacite, 10, "07:30", "09:00", reservations_existantes)

    # Mardi, 14 h à 14 h 20 -> Refusée : moins de 30 min
    with pytest.raises(ValueError, match="au moins 30 minutes"):
        valider_reservation(salle_capacite, 10, "14:00", "14:20", [])

    # Mardi, 8 h à 13 h -> Refusée : plus de 4 h
    with pytest.raises(ValueError, match="dépasser 4 heures"):
        valider_reservation(salle_capacite, 10, "08:00", "13:00", [])


def test_valider_reservation_conflit_personne():
    salle_capacite = 20
    # Salle S1 libre, mais Alice est déjà occupée dans S2
    res_personne = [
        {"id": 5, "salle_id": 2, "nom_salle": "S2", "personne": "Alice", "debut": "14:00", "fin": "16:00"}
    ]
    with pytest.raises(ValueError, match="Alice a déjà une réservation"):
        valider_reservation(
            capacite_salle=salle_capacite,
            participants=10,
            debut="15:00",
            fin="17:00",
            reservations_existantes=[],
            personne="Alice",
            reservations_personne=res_personne,
        )


def test_obtenir_semaine():
    # 2026-11-09 est un lundi
    lundi, dimanche, jours = obtenir_semaine("2026-11-09")
    assert lundi == date(2026, 11, 9)
    assert dimanche == date(2026, 11, 15)
    assert len(jours) == 7
    assert jours[0] == date(2026, 11, 9)
    assert jours[6] == date(2026, 11, 15)

    # Si on teste le mercredi 2026-11-11
    lundi2, dimanche2, jours2 = obtenir_semaine(date(2026, 11, 11))
    assert lundi2 == date(2026, 11, 9)
    assert dimanche2 == date(2026, 11, 15)


def test_calculer_taux_occupation():
    # 2 heures réservées sur 84 heures (5040 min)
    # (120 / 5040) * 100 = 2.38 % -> 2.4 %
    res = [{"debut": "10:00", "fin": "12:00"}]
    taux = calculer_taux_occupation(res)
    assert taux == 2.4
