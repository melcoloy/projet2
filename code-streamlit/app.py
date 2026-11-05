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
MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

st.set_page_config(page_title="Réservation de salles", page_icon="📅", layout="wide")


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


def formater_date(jour):
    """Rend une date en français : « lundi 9 novembre »."""
    return f"{JOURS[jour.weekday()].lower()} {jour.day} {MOIS[jour.month - 1]}"


def resume_salle(salle):
    """Résume une salle en une ligne, pour les légendes."""
    projecteur = "avec projecteur" if salle["projecteur"] else "sans projecteur"
    return (
        f"{salle['capacite']} places · {projecteur} · "
        f"ouverte de {salle['ouverture']} à {salle['fermeture']}"
    )


def carte_reservation(reservation):
    """Affiche une réservation du planning comme une pastille colorée."""
    st.markdown(
        "<div style='background:#eef2ff;border-left:3px solid #4f46e5;color:#1e1b4b;"
        "border-radius:6px;padding:6px 8px;margin-bottom:6px;line-height:1.35'>"
        f"<b>{reservation['debut']} → {reservation['fin']}</b><br>"
        f"<span style='font-size:0.85em'>{reservation['personne']}<br>"
        f"{reservation['participants']} participants</span></div>",
        unsafe_allow_html=True,
    )


with connexion() as conn:
    salles = conn.execute(
        "SELECT id, nom, capacite, projecteur, ouverture, fermeture FROM salles ORDER BY nom"
    ).fetchall()
    reservations = conn.execute(
        """
        SELECT r.id, s.nom AS salle, r.personne, r.date, r.debut, r.fin, r.participants
        FROM reservations r
        JOIN salles s ON s.id = r.salle_id
        ORDER BY r.date, r.debut, s.nom
        """
    ).fetchall()

salles_par_id = {salle["id"]: salle for salle in salles}
noms_des_salles = {salle_id: salle["nom"] for salle_id, salle in salles_par_id.items()}

st.title("📅 Réservation de salles")
st.caption(
    "Réservez une salle du bâtiment, sans conflit et dans la limite de sa capacité."
)

mesures = st.columns(3)
mesures[0].metric("Salles", len(salles))
mesures[1].metric("Réservations", len(reservations))
mesures[2].metric("Places au total", sum(salle["capacite"] for salle in salles))

if "message_reservation" in st.session_state:
    st.success(st.session_state.pop("message_reservation"))

onglet_planning, onglet_reserver, onglet_salles = st.tabs(
    ["Planning", "Réserver", "Salles"]
)

# --------------------------------------------------------------------------- #
# Planning                                                                      #
# --------------------------------------------------------------------------- #
with onglet_planning:
    if not salles:
        st.info("Aucune salle. Commencez par en ajouter une dans l'onglet « Salles ».")
    else:
        choix = st.columns([2, 2, 3])
        id_planning = choix[0].selectbox(
            "Salle",
            options=list(salles_par_id),
            format_func=lambda salle_id: noms_des_salles[salle_id],
            key="planning_salle",
        )
        date_planning = choix[1].date_input("Semaine du", key="planning_date")

        lundi = lundi_de_la_semaine(date_planning)
        dimanche = lundi + timedelta(days=6)
        choix[2].markdown(
            f"**{noms_des_salles[id_planning]}**  \n"
            f"<span style='opacity:0.7'>{resume_salle(salles_par_id[id_planning])}</span>",
            unsafe_allow_html=True,
        )

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

        st.caption(f"Du {formater_date(lundi)} au {formater_date(dimanche)}")

        reservations_par_jour = {}
        for reservation in reservations_semaine:
            reservations_par_jour.setdefault(reservation["date"], []).append(reservation)

        colonnes_jours = st.columns(7)
        for decalage, (colonne, nom_jour) in enumerate(zip(colonnes_jours, JOURS)):
            jour = lundi + timedelta(days=decalage)
            with colonne, st.container(border=True):
                st.markdown(
                    f"**{nom_jour}**  \n"
                    f"<span style='opacity:0.6'>{jour.day} {MOIS[jour.month - 1][:4]}.</span>",
                    unsafe_allow_html=True,
                )
                reservations_du_jour = reservations_par_jour.get(jour.isoformat(), [])
                if reservations_du_jour:
                    for reservation in reservations_du_jour:
                        carte_reservation(reservation)
                else:
                    st.caption("libre")

# --------------------------------------------------------------------------- #
# Réserver                                                                      #
# --------------------------------------------------------------------------- #
with onglet_reserver:
    if not salles:
        st.info("Aucune salle. Commencez par en ajouter une dans l'onglet « Salles ».")
    else:
        st.subheader("Réserver une salle")
        id_salle = st.selectbox(
            "Salle",
            options=list(salles_par_id),
            format_func=lambda salle_id: noms_des_salles[salle_id],
            key="reservation_salle",
        )
        salle_choisie = salles_par_id[id_salle]
        st.caption(resume_salle(salle_choisie))

        with st.form("reserver_salle", border=True):
            gauche, droite = st.columns(2)
            personne = gauche.text_input("Personne", key="reservation_personne")
            date_reservation = droite.date_input("Date", key="reservation_date")
            debut = gauche.time_input(
                "Heure de début",
                value=en_heure(salle_choisie["ouverture"]),
                key="reservation_debut",
            )
            fin = droite.time_input(
                "Heure de fin",
                value=en_heure(salle_choisie["ouverture"]),
                key="reservation_fin",
            )
            participants = gauche.number_input(
                "Nombre de participants",
                min_value=1,
                value=1,
                step=1,
                key="reservation_participants",
            )
            reserver = st.form_submit_button(
                "Réserver", key="reserver_salle", type="primary"
            )

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
                            reservations_du_jour = conn.execute(
                                "SELECT debut, fin FROM reservations WHERE salle_id = ? AND date = ?",
                                [id_salle, date_texte],
                            ).fetchall()
                            refus = verifier_reservation(
                                reservations_du_jour,
                                salle["capacite"],
                                debut_texte,
                                fin_texte,
                                participants,
                                salle["ouverture"],
                                salle["fermeture"],
                            )
                            if not refus:
                                conn.execute(
                                    "INSERT INTO reservations (salle_id, personne, date, debut, fin, participants)"
                                    " VALUES (?, ?, ?, ?, ?, ?)",
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

    st.subheader("Réservations")
    if reservations:
        for reservation in reservations:
            with st.container(border=True):
                colonnes = st.columns([2, 3, 4, 3, 2])
                colonnes[0].markdown(f"**{reservation['salle']}**")
                colonnes[1].write(reservation["personne"])
                colonnes[2].write(
                    f"{reservation['date']} · {reservation['debut']} → {reservation['fin']}"
                )
                colonnes[3].write(f"{reservation['participants']} participants")
                if colonnes[4].button("Annuler", key=f"annuler_{reservation['id']}"):
                    st.session_state["annulation_a_confirmer"] = reservation["id"]
                    st.rerun()

        id_a_annuler = st.session_state.get("annulation_a_confirmer")
        if id_a_annuler is not None:
            reservation = next((r for r in reservations if r["id"] == id_a_annuler), None)
            if reservation is None:
                st.session_state.pop("annulation_a_confirmer", None)
            else:
                st.warning(
                    f"Annuler la réservation de {reservation['personne']} "
                    f"le {reservation['date']} de {reservation['debut']} "
                    f"à {reservation['fin']} ?"
                )
                confirmation = st.columns([1, 1, 6])
                if confirmation[0].button(
                    "Confirmer", key="confirmer_annulation", type="primary"
                ):
                    with connexion() as conn:
                        conn.execute(
                            "DELETE FROM reservations WHERE id = ?", [id_a_annuler]
                        )
                    st.session_state.pop("annulation_a_confirmer", None)
                    st.session_state["message_reservation"] = "Réservation annulée."
                    st.rerun()
                if confirmation[1].button("Renoncer", key="renoncer_annulation"):
                    st.session_state.pop("annulation_a_confirmer", None)
                    st.rerun()
    else:
        st.info("Aucune réservation.")

# --------------------------------------------------------------------------- #
# Salles                                                                        #
# --------------------------------------------------------------------------- #
with onglet_salles:
    st.subheader("Salles")
    if salles:
        st.dataframe(
            [
                {
                    "Nom": salle["nom"],
                    "Capacité": salle["capacite"],
                    "Projecteur": bool(salle["projecteur"]),
                    "Ouverture": salle["ouverture"],
                    "Fermeture": salle["fermeture"],
                }
                for salle in salles
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "Capacité": st.column_config.NumberColumn(format="%d places"),
                "Projecteur": st.column_config.CheckboxColumn(),
            },
        )
    else:
        st.info("Aucune salle.")

    colonne_ajout, colonne_modif = st.columns(2)

    with colonne_ajout:
        st.markdown("##### Ajouter une salle")
        with st.form("ajouter_salle", border=True):
            nom = st.text_input("Nom", key="ajout_nom")
            capacite = st.number_input(
                "Capacité", min_value=1, value=10, key="ajout_capacite"
            )
            projecteur = st.checkbox("Projecteur", key="ajout_projecteur")
            heures = st.columns(2)
            ouverture = heures[0].time_input(
                "Ouverture", value=time(8, 0), key="ajout_ouverture"
            )
            fermeture = heures[1].time_input(
                "Fermeture", value=time(20, 0), key="ajout_fermeture"
            )
            ajouter = st.form_submit_button(
                "Ajouter", key="ajouter_salle", type="primary"
            )

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

    with colonne_modif:
        if salles:
            st.markdown("##### Modifier une salle")
            id_modifie = st.selectbox(
                "Salle à modifier",
                options=list(salles_par_id),
                format_func=lambda salle_id: noms_des_salles[salle_id],
                key="salle_a_modifier",
            )
            salle = salles_par_id[id_modifie]
            with st.form("modifier_salle", border=True):
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
                heures_modifiees = st.columns(2)
                ouverture_modifiee = heures_modifiees[0].time_input(
                    "Ouverture",
                    value=en_heure(salle["ouverture"]),
                    key=f"modif_ouverture_{id_modifie}",
                )
                fermeture_modifiee = heures_modifiees[1].time_input(
                    "Fermeture",
                    value=en_heure(salle["fermeture"]),
                    key=f"modif_fermeture_{id_modifie}",
                )
                enregistrer = st.form_submit_button(
                    "Enregistrer", key="enregistrer_salle", type="primary"
                )

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
                                "UPDATE salles SET nom = ?, nom_normalise = ?, capacite = ?,"
                                " projecteur = ?, ouverture = ?, fermeture = ? WHERE id = ?",
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

    if salles:
        with st.expander("Supprimer une salle"):
            with st.form("supprimer_salle", border=False):
                id_supprime = st.selectbox(
                    "Salle à supprimer",
                    options=list(salles_par_id),
                    format_func=lambda salle_id: noms_des_salles[salle_id],
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
