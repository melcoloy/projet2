from datetime import timedelta

OUVERTURE_BATIMENT = "08:00"
FERMETURE_BATIMENT = "20:00"


def lundi_de_la_semaine(jour):
    """Renvoie le lundi de la semaine contenant jour."""
    return jour - timedelta(days=jour.weekday())


def _en_minutes(heure):
    heures, minutes = heure.split(":")
    return int(heures) * 60 + int(minutes)


def verifier_horaires_salle(ouverture, fermeture):
    """Renvoie un message de refus, ou None si les horaires de la salle sont valables.

    Une salle ouvre et ferme dans les horaires du bâtiment, et reste ouverte
    assez longtemps pour accueillir une réservation.
    """
    ouverture_minutes = _en_minutes(ouverture)
    fermeture_minutes = _en_minutes(fermeture)

    if fermeture_minutes <= ouverture_minutes:
        return "La salle doit fermer après son ouverture."

    if ouverture_minutes < _en_minutes(OUVERTURE_BATIMENT) or fermeture_minutes > _en_minutes(
        FERMETURE_BATIMENT
    ):
        return (
            f"Le bâtiment est ouvert de {OUVERTURE_BATIMENT} à {FERMETURE_BATIMENT}."
        )

    if fermeture_minutes - ouverture_minutes < 30:
        return "La salle doit rester ouverte au moins 30 minutes."

    return None


def verifier_reservation(
    reservations,
    capacite,
    debut,
    fin,
    participants,
    ouverture=OUVERTURE_BATIMENT,
    fermeture=FERMETURE_BATIMENT,
):
    """Renvoie un message de refus, ou None si la réservation est acceptée.

    reservations contient les réservations de la salle à la même date.
    ouverture et fermeture sont les horaires d'ouverture de la salle.
    """
    debut_minutes = _en_minutes(debut)
    fin_minutes = _en_minutes(fin)

    if fin_minutes <= debut_minutes:
        return "La réservation doit se terminer après son début."

    if debut_minutes < _en_minutes(ouverture) or fin_minutes > _en_minutes(fermeture):
        return f"La salle est ouverte de {ouverture} à {fermeture}."

    duree = fin_minutes - debut_minutes
    if duree < 30:
        return "La réservation doit durer au moins 30 minutes."
    if duree > 4 * 60:
        return "La réservation doit durer au plus 4 heures."

    if participants < 1:
        return "Le nombre de participants doit être au moins 1."
    if participants > capacite:
        return f"La salle ne peut accueillir que {capacite} participants."

    for reservation in reservations:
        debut_existant = _en_minutes(reservation["debut"])
        fin_existante = _en_minutes(reservation["fin"])
        if debut_minutes < fin_existante and debut_existant < fin_minutes:
            return "La salle est déjà réservée sur ce créneau."

    return None
