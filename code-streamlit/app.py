import sqlite3
from contextlib import closing, contextmanager

import streamlit as st

from base import ouvrir_base


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
    salles_par_id = {salle["id"]: salle for salle in salles}
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
