from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple, Union


def heure_en_minutes(h: Union[str, time]) -> int:
    """Convertit une heure ('HH:MM' ou datetime.time) en minutes depuis minuit."""
    if isinstance(h, str):
        parties = h.strip().split(":")
        if len(parties) != 2:
            raise ValueError("Format d'heure invalide. Utilisez 'HH:MM'.")
        heures, minutes = int(parties[0]), int(parties[1])
    elif isinstance(h, time):
        heures, minutes = h.hour, h.minute
    else:
        raise TypeError("L'heure doit être une chaîne 'HH:MM' ou un datetime.time.")
    return heures * 60 + minutes


def minutes_en_heure(m: int) -> str:
    """Convertit des minutes depuis minuit en chaîne 'HH:MM'."""
    heures = m // 60
    minutes = m % 60
    return f"{heures:02d}:{minutes:02d}"


def valider_horaires(debut: Union[str, time], fin: Union[str, time]) -> Tuple[int, int, int]:
    """
    Vérifie que :
    - La réservation a lieu entre 8h et 20h.
    - L'heure de fin est après l'heure de début.
    - La durée est comprise entre 30 min et 4 h (240 min).
    Retourne (debut_min, fin_min, duree_min).
    """
    debut_min = heure_en_minutes(debut)
    fin_min = heure_en_minutes(fin)

    limite_debut = 8 * 60   # 08:00 = 480 min
    limite_fin = 20 * 60    # 20:00 = 1200 min

    if debut_min < limite_debut:
        raise ValueError("Une réservation ne peut pas commencer avant 8 h.")
    if fin_min > limite_fin:
        raise ValueError("Une réservation ne peut pas se terminer après 20 h.")
    if fin_min <= debut_min:
        raise ValueError("L'heure de fin doit être postérieure à l'heure de début.")

    duree = fin_min - debut_min
    if duree < 30:
        raise ValueError("Une réservation doit durer au moins 30 minutes.")
    if duree > 240:
        raise ValueError("Une réservation ne peut pas dépasser 4 heures.")

    return debut_min, fin_min, duree


def valider_capacite(participants: int, capacite: int) -> None:
    """Vérifie que les participants sont positifs et ne dépassent pas la capacité."""
    if participants <= 0:
        raise ValueError("Le nombre de participants doit être supérieur à zéro.")
    if participants > capacite:
        raise ValueError(
            f"Le nombre de participants ({participants}) dépasse la capacité de la salle ({capacite})."
        )


def sont_en_chevauchement(
    debut1: Union[str, time], fin1: Union[str, time],
    debut2: Union[str, time], fin2: Union[str, time]
) -> bool:
    """
    Deux créneaux se chevauchent si max(debut1, debut2) < min(fin1, fin2).
    Finir à 12h et commencer à 12h ne se chevauchent pas.
    """
    d1 = heure_en_minutes(debut1)
    f1 = heure_en_minutes(fin1)
    d2 = heure_en_minutes(debut2)
    f2 = heure_en_minutes(fin2)

    return max(d1, d2) < min(f1, f2)


def valider_reservation(
    capacite_salle: int,
    participants: int,
    debut: Union[str, time],
    fin: Union[str, time],
    reservations_existantes: List[dict],
    reservation_id_ignore: Optional[int] = None,
) -> None:
    """
    Valide l'ensemble des règles métier pour une réservation :
    - Plage horaire 8h-20h et durée 30 min à 4h
    - Capacité
    - Chevauchement avec les réservations existantes du même jour et même salle
    """
    valider_horaires(debut, fin)
    valider_capacite(participants, capacite_salle)

    for res in reservations_existantes:
        if reservation_id_ignore is not None and res.get("id") == reservation_id_ignore:
            continue
        if sont_en_chevauchement(debut, fin, res["debut"], res["fin"]):
            raise ValueError(
                f"La réservation chevauche une réservation existante ({res['debut']} - {res['fin']})."
            )


def obtenir_semaine(date_ref: Union[str, date]) -> Tuple[date, date, List[date]]:
    """
    Renvoie le lundi, le dimanche et la liste des 7 jours de la semaine contenant date_ref.
    La semaine va du lundi au dimanche.
    """
    if isinstance(date_ref, str):
        d = datetime.strptime(date_ref, "%Y-%m-%d").date()
    elif isinstance(date_ref, date):
        d = date_ref
    else:
        raise TypeError("date_ref doit être une chaîne 'YYYY-MM-DD' ou un datetime.date.")

    lundi = d - timedelta(days=d.weekday())
    dimanche = lundi + timedelta(days=6)
    jours = [lundi + timedelta(days=i) for i in range(7)]
    return lundi, dimanche, jours


def calculer_taux_occupation(reservations: List[dict]) -> float:
    """
    Calcule le taux d'occupation sur la semaine (lundi-dimanche de 8h à 20h = 12h/jour x 7 jours = 84h = 5040 minutes).
    Retourne un pourcentage arrondi à 1 décimale.
    """
    total_minutes_ouvrables = 7 * 12 * 60  # 5040 min
    minutes_reservees = 0

    for res in reservations:
        try:
            d_min = heure_en_minutes(res["debut"])
            f_min = heure_en_minutes(res["fin"])
            minutes_reservees += max(0, f_min - d_min)
        except Exception:
            pass

    if total_minutes_ouvrables == 0:
        return 0.0

    taux = (minutes_reservees / total_minutes_ouvrables) * 100
    return round(taux, 1)

