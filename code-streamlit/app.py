import streamlit as st

from base import ouvrir_base


def nom_salle_utilise(conn, nom, salle_id=None):
    requete = "SELECT 1 FROM salles WHERE nom = ?"
    parametres = [nom]
    if salle_id is not None:
        requete += " AND id != ?"
        parametres.append(salle_id)
    return conn.execute(requete, parametres).fetchone() is not None


st.title("Réservation de salles")

with ouvrir_base() as conn:
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
        with ouvrir_base() as conn:
            deja_utilise = nom_salle_utilise(conn, candidat)
            if not deja_utilise:
                conn.execute(
                    "INSERT INTO salles (nom, capacite, projecteur) VALUES (?, ?, ?)",
                    [candidat, capacite, int(projecteur)],
                )
        if deja_utilise:
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
        nom = st.text_input(
            "Nom", value=salle["nom"], key=f"modif_nom_{id_modifie}"
        )
        capacite = st.number_input(
            "Capacité",
            min_value=1,
            value=salle["capacite"],
            key=f"modif_capacite_{id_modifie}",
        )
        projecteur = st.checkbox(
            "Projecteur",
            value=bool(salle["projecteur"]),
            key=f"modif_projecteur_{id_modifie}",
        )
        enregistrer = st.form_submit_button("Enregistrer", key="enregistrer_salle")

    if enregistrer:
        candidat = nom.strip()
        if not candidat:
            st.error("Le nom est obligatoire.")
        else:
            with ouvrir_base() as conn:
                deja_utilise = nom_salle_utilise(conn, candidat, id_modifie)
                if not deja_utilise:
                    conn.execute(
                        "UPDATE salles SET nom = ?, capacite = ?, projecteur = ? WHERE id = ?",
                        [candidat, capacite, int(projecteur), id_modifie],
                    )
            if deja_utilise:
                st.error(f"La salle « {candidat} » existe déjà.")
            else:
                st.rerun()

    st.subheader("Supprimer une salle")
    id_supprime = st.selectbox(
        "Salle à supprimer",
        options=list(salles_par_id),
        format_func=lambda salle_id: salles_par_id[salle_id]["nom"],
        key="salle_a_supprimer",
    )
    st.caption("Les réservations de cette salle seront aussi supprimées.")
    if st.button("Supprimer", key="supprimer_salle"):
        with ouvrir_base() as conn:
            conn.execute("DELETE FROM salles WHERE id = ?", [id_supprime])
        st.rerun()
