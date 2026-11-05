import sqlite3
from contextlib import closing, contextmanager
from datetime import time

import streamlit as st

from base import ouvrir_base
from regles import verifier_reservation


@contextmanager
def connexion():
    with closing(ouvrir_base()) as conn, conn:
        yield conn


def normaliser_nom(nom):
    return nom.strip().casefold()


st.title("Réservation de salles")

with connexion() as conn:
    salles = conn.execute(
        "SELECT id, nom, capacite, projecteur FROM salles ORDER BY nom"
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
    ajouter = st.form_submit_button("Ajouter", key="ajouter_salle")

if ajouter:
    candidat = nom.strip()
    if not candidat:
        st.error("Le nom est obligatoire.")
    else:
        try:
            with connexion() as conn:
                conn.execute(
                    "INSERT INTO salles (nom, nom_normalise, capacite, projecteur) VALUES (?, ?, ?, ?)",
                    [candidat, normaliser_nom(candidat), capacite, int(projecteur)],
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
        enregistrer = st.form_submit_button("Enregistrer", key="enregistrer_salle")

    if enregistrer:
        candidat = nom_modifie.strip()
        if not candidat:
            st.error("Le nom est obligatoire.")
        else:
            try:
                with connexion() as conn:
                    conn.execute(
                        "UPDATE salles SET nom = ?, nom_normalise = ?, capacite = ?, projecteur = ? WHERE id = ?",
                        [
                            candidat,
                            normaliser_nom(candidat),
                            capacite_modifiee,
                            int(projecteur_modifie),
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
                        "SELECT capacite FROM salles WHERE id = ?", [id_salle]
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
            with connexion() as conn:
                conn.execute(
                    "DELETE FROM reservations WHERE id = ?", [reservation["id"]]
                )
            st.rerun()
else:
    st.info("Aucune réservation.")
