def _en_minutes(heure):
    heures, minutes = heure.split(":")
    return int(heures) * 60 + int(minutes)


def verifier_reservation(reservations, capacite, debut, fin, participants):
    """Renvoie un message de refus, ou None si la réservation est acceptée.

    reservations contient les réservations de la salle à la même date.
    """
    debut_minutes = _en_minutes(debut)
    fin_minutes = _en_minutes(fin)

    if fin_minutes <= debut_minutes:
        return "La réservation doit se terminer après son début."

    if debut_minutes < 8 * 60 or fin_minutes > 20 * 60:
        return "La réservation doit avoir lieu entre 8 h et 20 h."

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
