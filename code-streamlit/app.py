import sqlite3
from contextlib import closing, contextmanager
from datetime import time, timedelta

import streamlit as st

from base import ouvrir_base
from regles import (
    lundi_de_la_semaine,
    verifier_horaires_salle,
    verifier_reservation,
)

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


@contextmanager
def connexion():
    with closing(ouvrir_base()) as conn, conn:
        yield conn


def normaliser_nom(nom):
    return nom.strip().casefold()


def en_heure(texte):
    """Convertit « HH:MM » en datetime.time, pour les champs du formulaire."""
    heures, minutes = texte.split(":")
    return time(int(heures), int(minutes))


st.title("Réservation de salles")

with connexion() as conn:
    salles = conn.execute(
        "SELECT id, nom, capacite, projecteur, ouverture, fermeture FROM salles ORDER BY nom"
    ).fetchall()

salles_par_id = {salle["id"]: salle for salle in salles}

st.header("Salles")
if salles:
    st.dataframe(
        [
            {
                "Nom": salle["nom"],
                "Capacité": salle["capacite"],
                "Projecteur": "oui" if salle["projecteur"] else "non",
                "Ouverture": salle["ouverture"],
                "Fermeture": salle["fermeture"],
            }
            for salle in salles
        ]
    )
else:
    st.info("Aucune salle.")

st.subheader("Ajouter une salle")
with st.form("ajouter_salle"):
    nom = st.text_input("Nom", key="ajout_nom")
    capacite = st.number_input("Capacité", min_value=1, value=10, key="ajout_capacite")
    projecteur = st.checkbox("Projecteur", key="ajout_projecteur")
    ouverture = st.time_input("Ouverture", value=time(8, 0), key="ajout_ouverture")
    fermeture = st.time_input("Fermeture", value=time(20, 0), key="ajout_fermeture")
    ajouter = st.form_submit_button("Ajouter", key="ajouter_salle")

if ajouter:
    candidat = nom.strip()
    ouverture_texte = ouverture.strftime("%H:%M")
    fermeture_texte = fermeture.strftime("%H:%M")
    refus_salle = verifier_horaires_salle(ouverture_texte, fermeture_texte)
    if not candidat:
        st.error("Le nom est obligatoire.")
    elif refus_salle:
        st.error(refus_salle)
    else:
        try:
            with connexion() as conn:
                conn.execute(
                    "INSERT INTO salles (nom, nom_normalise, capacite, projecteur, ouverture, fermeture)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        candidat,
                        normaliser_nom(candidat),
                        capacite,
                        int(projecteur),
                        ouverture_texte,
                        fermeture_texte,
                    ],
                )
        except sqlite3.IntegrityError:
            st.error(f"La salle « {candidat} » existe déjà.")
        else:
            st.rerun()

if salles:
    st.subheader("Modifier une salle")
    id_modifie = st.selectbox(
        "Salle à modifier",
        options=list(salles_par_id),
        format_func=lambda salle_id: salles_par_id[salle_id]["nom"],
        key="salle_a_modifier",
    )
    salle = salles_par_id[id_modifie]
    with st.form("modifier_salle"):
        nom_modifie = st.text_input(
            "Nom", value=salle["nom"], key=f"modif_nom_{id_modifie}"
        )
        capacite_modifiee = st.number_input(
            "Capacité",
            min_value=1,
            value=salle["capacite"],
            key=f"modif_capacite_{id_modifie}",
        )
        projecteur_modifie = st.checkbox(
            "Projecteur",
            value=bool(salle["projecteur"]),
            key=f"modif_projecteur_{id_modifie}",
        )
        ouverture_modifiee = st.time_input(
            "Ouverture",
            value=en_heure(salle["ouverture"]),
            key=f"modif_ouverture_{id_modifie}",
        )
        fermeture_modifiee = st.time_input(
            "Fermeture",
            value=en_heure(salle["fermeture"]),
            key=f"modif_fermeture_{id_modifie}",
        )
        enregistrer = st.form_submit_button("Enregistrer", key="enregistrer_salle")

    if enregistrer:
        candidat = nom_modifie.strip()
        ouverture_texte = ouverture_modifiee.strftime("%H:%M")
        fermeture_texte = fermeture_modifiee.strftime("%H:%M")
        refus_salle = verifier_horaires_salle(ouverture_texte, fermeture_texte)
        if not candidat:
            st.error("Le nom est obligatoire.")
        elif refus_salle:
            st.error(refus_salle)
        else:
            try:
                with connexion() as conn:
                    conn.execute(
                        "UPDATE salles SET nom = ?, nom_normalise = ?, capacite = ?, projecteur = ?,"
                        " ouverture = ?, fermeture = ? WHERE id = ?",
                        [
                            candidat,
                            normaliser_nom(candidat),
                            capacite_modifiee,
                            int(projecteur_modifie),
                            ouverture_texte,
                            fermeture_texte,
                            id_modifie,
                        ],
                    )
            except sqlite3.IntegrityError:
                st.error(f"La salle « {candidat} » existe déjà.")
            else:
                st.rerun()

    st.subheader("Supprimer une salle")
    with st.form("supprimer_salle"):
        id_supprime = st.selectbox(
            "Salle à supprimer",
            options=list(salles_par_id),
            format_func=lambda salle_id: salles_par_id[salle_id]["nom"],
            key="salle_a_supprimer",
        )
        st.caption("Les réservations de cette salle seront aussi supprimées.")
        confirmer = st.checkbox(
            "Je confirme la suppression de cette salle et de ses réservations.",
            key=f"confirmer_suppression_{id_supprime}",
        )
        supprimer = st.form_submit_button("Supprimer", key="supprimer_salle")

    if supprimer:
        if not confirmer:
            st.error("Veuillez confirmer la suppression.")
        else:
            with connexion() as conn:
                conn.execute("DELETE FROM salles WHERE id = ?", [id_supprime])
            st.rerun()

if salles:
    st.subheader("Réserver une salle")
    with st.form("reserver_salle"):
        id_salle = st.selectbox(
            "Salle",
            options=list(salles_par_id),
            format_func=lambda salle_id: salles_par_id[salle_id]["nom"],
            key="reservation_salle",
        )
        personne = st.text_input("Personne", key="reservation_personne")
        date_reservation = st.date_input("Date", key="reservation_date")
        debut = st.time_input(
            "Heure de début", value=time(8, 0), key="reservation_debut"
        )
        fin = st.time_input("Heure de fin", value=time(9, 0), key="reservation_fin")
        participants = st.number_input(
            "Nombre de participants",
            min_value=1,
            value=1,
            step=1,
            key="reservation_participants",
        )
        reserver = st.form_submit_button("Réserver", key="reserver_salle")

    if reserver:
        personne_texte = personne.strip()
        date_texte = date_reservation.isoformat()
        debut_texte = debut.strftime("%H:%M")
        fin_texte = fin.strftime("%H:%M")
        refus = None
        if not personne_texte:
            refus = "Le nom de la personne est obligatoire."
        else:
            try:
                with connexion() as conn:
                    salle = conn.execute(
                        "SELECT capacite, ouverture, fermeture FROM salles WHERE id = ?",
                        [id_salle],
                    ).fetchone()
                    if salle is None:
                        refus = "Cette salle n'existe plus."
                    else:
                        reservations = conn.execute(
                            "SELECT debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
                            [id_salle, date_texte],
                        ).fetchall()
                        refus = verifier_reservation(
                            reservations,
                            salle["capacite"],
                            debut_texte,
                            fin_texte,
                            participants,
                            salle["ouverture"],
                            salle["fermeture"],
                        )
                        if not refus:
                            conn.execute(
                                "INSERT INTO reservations (salle_id, personne, date, debut, fin, participants) VALUES (?, ?, ?, ?, ?, ?)",
                                [
                                    id_salle,
                                    personne_texte,
                                    date_texte,
                                    debut_texte,
                                    fin_texte,
                                    participants,
                                ],
                            )
            except sqlite3.IntegrityError:
                refus = "Cette salle n'existe plus."
        if refus:
            st.error(refus)
        else:
            st.session_state["message_reservation"] = (
                f"Réservation enregistrée pour {personne_texte} le {date_texte} "
                f"de {debut_texte} à {fin_texte}."
            )
            st.rerun()

if "message_reservation" in st.session_state:
    st.success(st.session_state.pop("message_reservation"))

if salles:
    st.subheader("Planning d'une salle")
    id_planning = st.selectbox(
        "Salle",
        options=list(salles_par_id),
        format_func=lambda salle_id: salles_par_id[salle_id]["nom"],
        key="planning_salle",
    )
    date_planning = st.date_input("Date de la semaine", key="planning_date")
    lundi = lundi_de_la_semaine(date_planning)
    dimanche = lundi + timedelta(days=6)

    with connexion() as conn:
        reservations_semaine = conn.execute(
            """
            SELECT personne, date, debut, fin, participants
            FROM reservations
            WHERE salle_id = ? AND date BETWEEN ? AND ?
            ORDER BY date, debut
            """,
            [id_planning, lundi.isoformat(), dimanche.isoformat()],
        ).fetchall()

    reservations_par_jour = {}
    for reservation in reservations_semaine:
        reservations_par_jour.setdefault(reservation["date"], []).append(reservation)

    for decalage, nom_jour in enumerate(JOURS):
        jour = lundi + timedelta(days=decalage)
        st.markdown(f"**{nom_jour} {jour.isoformat()}**")
        reservations_du_jour = reservations_par_jour.get(jour.isoformat(), [])
        if reservations_du_jour:
            st.dataframe(
                [
                    {
                        "Personne": reservation["personne"],
                        "Début": reservation["debut"],
                        "Fin": reservation["fin"],
                        "Participants": reservation["participants"],
                    }
                    for reservation in reservations_du_jour
                ],
                hide_index=True,
            )
        else:
            st.caption("Aucune réservation.")

with connexion() as conn:
    reservations = conn.execute(
        """
        SELECT r.id, s.nom AS salle, r.personne, r.date, r.debut, r.fin, r.participants
        FROM reservations r
        JOIN salles s ON s.id = r.salle_id
        ORDER BY r.date, r.debut, s.nom
        """
    ).fetchall()

st.subheader("Réservations")
if reservations:
    colonnes_entete = st.columns([2, 2, 2, 1, 1, 1, 1])
    for colonne, libelle in zip(
        colonnes_entete,
        ["Salle", "Personne", "Date", "Début", "Fin", "Participants", ""],
    ):
        colonne.markdown(f"**{libelle}**")
    for reservation in reservations:
        colonnes = st.columns([2, 2, 2, 1, 1, 1, 1])
        colonnes[0].write(reservation["salle"])
        colonnes[1].write(reservation["personne"])
        colonnes[2].write(reservation["date"])
        colonnes[3].write(reservation["debut"])
        colonnes[4].write(reservation["fin"])
        colonnes[5].write(str(reservation["participants"]))
        if colonnes[6].button("Annuler", key=f"annuler_{reservation['id']}"):
            st.session_state["annulation_a_confirmer"] = reservation["id"]
            st.rerun()

    id_a_annuler = st.session_state.get("annulation_a_confirmer")
    if id_a_annuler is not None:
        reservation = next(
            (r for r in reservations if r["id"] == id_a_annuler), None
        )
        if reservation is None:
            st.session_state.pop("annulation_a_confirmer", None)
        else:
            st.warning(
                f"Annuler la réservation de {reservation['personne']} "
                f"le {reservation['date']} de {reservation['debut']} "
                f"à {reservation['fin']} ?"
            )
            if st.button("Confirmer l'annulation", key="confirmer_annulation"):
                with connexion() as conn:
                    conn.execute(
                        "DELETE FROM reservations WHERE id = ?", [id_a_annuler]
                    )
                st.session_state.pop("annulation_a_confirmer", None)
                st.session_state["message_reservation"] = "Réservation annulée."
                st.rerun()
            if st.button("Renoncer", key="renoncer_annulation"):
                st.session_state.pop("annulation_a_confirmer", None)
                st.rerun()
else:
    st.info("Aucune réservation.")
