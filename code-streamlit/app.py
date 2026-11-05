import csv
import io
from datetime import date, datetime, time
import streamlit as st

from base import ouvrir_base
from db import (
    ajouter_reservation,
    ajouter_salle,
    annuler_reservation,
    lister_reservations,
    lister_salles,
    modifier_salle,
    obtenir_salle,
    supprimer_salle,
    trouver_salles_libres,
)
from regles import (
    calculer_taux_occupation,
    minutes_en_heure,
    obtenir_semaine,
)

st.set_page_config(page_title="Réservation de salles", page_icon="🏢", layout="wide")

st.title("🏢 Système de Réservation de Salles")
st.caption("Gestion simple des salles et réservations sans conflit d'horaires.")

# Onglets principaux
tab_planning, tab_reserver, tab_annuler, tab_salles, tab_recherche = st.tabs([
    "📅 Planning de la semaine",
    "✍️ Réserver une salle",
    "❌ Annuler une réservation",
    "🏢 Gestion des salles",
    "🔍 Chercher une salle libre",
])

# ----------------------------------------------------------------------
# Onglet 1 : Planning d'une salle sur une semaine
# ----------------------------------------------------------------------
with tab_planning:
    st.header("Planning hebdomadaire")

    with ouvrir_base() as conn:
        salles = lister_salles(conn)

    if not salles:
        st.info("Aucune salle enregistrée pour le moment. Rendez-vous dans l'onglet 'Gestion des salles' pour en créer une.")
    else:
        col_salle, col_date = st.columns(2)
        with col_salle:
            options_salles = {s["nom"]: s["id"] for s in salles}
            nom_salle_choisie = st.selectbox(
                "Choisir une salle",
                options=list(options_salles.keys()),
                key="planning_salle",
            )
            salle_id = options_salles[nom_salle_choisie]
            salle_actuelle = next(s for s in salles if s["id"] == salle_id)

        with col_date:
            date_choisie = st.date_input(
                "Semaine contenant le",
                value=date(2026, 11, 9),
                key="planning_date",
            )

        lundi, dimanche, jours_semaine = obtenir_semaine(date_choisie)
        st.markdown(
            f"**Semaine du lundi {lundi.strftime('%d/%m/%Y')} au dimanche {dimanche.strftime('%d/%m/%Y')}**"
        )
        st.write(
            f"Salle **{salle_actuelle['nom']}** — Capacité : **{salle_actuelle['capacite']} places** — "
            f"Projecteur : **{'Oui' if salle_actuelle['projecteur'] else 'Non'}**"
        )

        # Récupérer les réservations de la semaine
        with ouvrir_base() as conn:
            reservations = lister_reservations(
                conn,
                salle_id=salle_id,
                date_debut=lundi.strftime("%Y-%m-%d"),
                date_fin=dimanche.strftime("%Y-%m-%d"),
            )
            reservations_dict = [dict(r) for r in reservations]

        # Taux d'occupation
        taux = calculer_taux_occupation(reservations_dict)
        col_taux, col_export = st.columns([1, 2])
        with col_taux:
            st.metric("Taux d'occupation hebdomadaire", f"{taux} %")

        with col_export:
            # Exporter le planning en CSV
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer, delimiter=";")
            writer.writerow(["Salle", "Date", "Jour", "Debut", "Fin", "Personne", "Participants"])
            noms_jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
            for r in reservations_dict:
                d_obj = datetime.strptime(r["date"], "%Y-%m-%d").date()
                jour_nom = noms_jours[d_obj.weekday()]
                writer.writerow([
                    salle_actuelle["nom"],
                    r["date"],
                    jour_nom,
                    r["debut"],
                    r["fin"],
                    r["personne"],
                    r["participants"],
                ])

            st.download_button(
                label="📥 Exporter le planning (CSV)",
                data=csv_buffer.getvalue().encode("utf-8-sig"),
                file_name=f"planning_{salle_actuelle['nom']}_{lundi.strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

        st.divider()

        # Affichage jour par jour (Lundi -> Dimanche)
        noms_jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        cols = st.columns(7)

        for idx, (col_jour, jour_date) in enumerate(zip(cols, jours_semaine)):
            date_str = jour_date.strftime("%Y-%m-%d")
            res_du_jour = [r for r in reservations_dict if r["date"] == date_str]

            with col_jour:
                st.markdown(f"**{noms_jours[idx]}**")
                st.caption(jour_date.strftime("%d/%m"))
                if not res_du_jour:
                    st.write("—")
                else:
                    for r in res_du_jour:
                        st.info(
                            f"**{r['debut']} - {r['fin']}**\n\n"
                            f"👤 {r['personne']}\n\n"
                            f"👥 {r['participants']} pers."
                        )

        # Tableau détaillé
        if reservations_dict:
            st.subheader("Détail des réservations")
            donnees_tableau = []
            for r in reservations_dict:
                d_obj = datetime.strptime(r["date"], "%Y-%m-%d").date()
                donnees_tableau.append({
                    "Date": r["date"],
                    "Jour": noms_jours[d_obj.weekday()],
                    "Début": r["debut"],
                    "Fin": r["fin"],
                    "Réservé par": r["personne"],
                    "Participants": r["participants"],
                })
            st.dataframe(donnees_tableau, use_container_width=True)


# ----------------------------------------------------------------------
# Onglet 2 : Réserver une salle
# ----------------------------------------------------------------------
with tab_reserver:
    st.header("Faire une nouvelle réservation")

    with ouvrir_base() as conn:
        salles = lister_salles(conn)

    if not salles:
        st.warning("Veuillez d'abord ajouter une salle dans l'onglet 'Gestion des salles'.")
    else:
        options_salles_res = {
            f"{s['nom']} (capacité: {s['capacite']}, projecteur: {'oui' if s['projecteur'] else 'non'})": s["id"]
            for s in salles
        }

        with st.form("form_reservation"):
            salle_selectionnee = st.selectbox("Salle", options=list(options_salles_res.keys()))
            salle_id = options_salles_res[salle_selectionnee]

            personne = st.text_input("Nom de la personne")
            date_res = st.date_input("Date", value=date(2026, 11, 9))

            col_h1, col_h2 = st.columns(2)
            with col_h1:
                debut_res = st.time_input("Heure de début (entre 08:00 et 20:00)", value=time(10, 0))
            with col_h2:
                fin_res = st.time_input("Heure de fin (durée entre 30 min et 4 h)", value=time(11, 0))

            participants = st.number_input("Nombre de participants", min_value=1, value=5, step=1)

            submit_res = st.form_submit_button("Réserver la salle")

        if submit_res:
            debut_str = f"{debut_res.hour:02d}:{debut_res.minute:02d}"
            fin_str = f"{fin_res.hour:02d}:{fin_res.minute:02d}"
            date_str = date_res.strftime("%Y-%m-%d")

            try:
                with ouvrir_base() as conn:
                    ajouter_reservation(
                        conn=conn,
                        salle_id=salle_id,
                        personne=personne,
                        date_str=date_str,
                        debut_str=debut_str,
                        fin_str=fin_str,
                        participants=participants,
                    )
                st.success(f"Réservation confirmée pour {personne} le {date_str} de {debut_str} à {fin_str} !")
                st.rerun()
            except ValueError as err:
                st.error(f"Erreur de réservation : {err}")


# ----------------------------------------------------------------------
# Onglet 3 : Annuler une réservation
# ----------------------------------------------------------------------
with tab_annuler:
    st.header("Annuler une réservation")

    with ouvrir_base() as conn:
        toutes_reservations = lister_reservations(conn)

    if not toutes_reservations:
        st.info("Aucune réservation enregistrée.")
    else:
        st.write("Sélectionnez la réservation à annuler :")
        dict_options_res = {}
        for r in toutes_reservations:
            cle = f"#{r['id']} — Salle {r['nom_salle']} le {r['date']} ({r['debut']}-{r['fin']}) par {r['personne']} ({r['participants']} pers.)"
            dict_options_res[cle] = r["id"]

        res_a_annuler = st.selectbox("Réservation", options=list(dict_options_res.keys()))

        if st.button("Annuler cette réservation", type="primary"):
            id_a_supprimer = dict_options_res[res_a_annuler]
            with ouvrir_base() as conn:
                annuler_reservation(conn, id_a_supprimer)
            st.success("La réservation a été annulée avec succès.")
            st.rerun()


# ----------------------------------------------------------------------
# Onglet 4 : Gestion des salles (Ajouter, modifier, supprimer)
# ----------------------------------------------------------------------
with tab_salles:
    st.header("Gestion des salles")

    with ouvrir_base() as conn:
        salles_actuelles = lister_salles(conn)

    # Affichage des salles
    st.subheader("Salles existantes")
    if salles_actuelles:
        donnees_salles = [
            {
                "ID": s["id"],
                "Nom": s["nom"],
                "Capacité": s["capacite"],
                "Projecteur": "Oui" if s["projecteur"] else "Non",
            }
            for s in salles_actuelles
        ]
        st.dataframe(donnees_salles, use_container_width=True)
    else:
        st.info("Aucune salle enregistrée.")

    st.divider()

    col_add, col_edit, col_del = st.columns(3)

    # 1. Ajouter une salle
    with col_add:
        st.subheader("Ajouter une salle")
        with st.form("form_ajout_salle"):
            nom_nouvelle = st.text_input("Nom de la salle")
            capa_nouvelle = st.number_input("Capacité", min_value=1, value=10, step=1)
            proj_nouvelle = st.checkbox("Projecteur disponible")
            submit_ajout = st.form_submit_button("Ajouter")

        if submit_ajout:
            try:
                with ouvrir_base() as conn:
                    ajouter_salle(conn, nom_nouvelle, capa_nouvelle, proj_nouvelle)
                st.success(f"Salle '{nom_nouvelle}' ajoutée avec succès.")
                st.rerun()
            except ValueError as err:
                st.error(f"Erreur : {err}")

    # 2. Modifier une salle
    with col_edit:
        st.subheader("Modifier une salle")
        if salles_actuelles:
            options_edit = {s["nom"]: s for s in salles_actuelles}
            salle_edit_nom = st.selectbox("Salle à modifier", options=list(options_edit.keys()), key="select_edit")
            salle_obj = options_edit[salle_edit_nom]

            with st.form("form_edit_salle"):
                nom_modif = st.text_input("Nouveau nom", value=salle_obj["nom"])
                capa_modif = st.number_input("Nouvelle capacité", min_value=1, value=int(salle_obj["capacite"]), step=1)
                proj_modif = st.checkbox("Projecteur disponible", value=bool(salle_obj["projecteur"]))
                submit_modif = st.form_submit_button("Enregistrer les modifications")

            if submit_modif:
                try:
                    with ouvrir_base() as conn:
                        modifier_salle(conn, salle_obj["id"], nom_modif, capa_modif, proj_modif)
                    st.success("Salle modifiée avec succès.")
                    st.rerun()
                except ValueError as err:
                    st.error(f"Erreur : {err}")
        else:
            st.caption("Aucune salle à modifier.")

    # 3. Supprimer une salle
    with col_del:
        st.subheader("Supprimer une salle")
        if salles_actuelles:
            options_del = {s["nom"]: s["id"] for s in salles_actuelles}
            salle_del_nom = st.selectbox("Salle à supprimer", options=list(options_del.keys()), key="select_del")
            salle_del_id = options_del[salle_del_nom]

            st.caption("⚠️ La suppression d'une salle supprime automatiquement toutes ses réservations associées.")
            if st.button("Supprimer définitivement", type="primary", key="btn_del_salle"):
                with ouvrir_base() as conn:
                    supprimer_salle(conn, salle_del_id)
                st.success(f"Salle '{salle_del_nom}' supprimée.")
                st.rerun()
        else:
            st.caption("Aucune salle à supprimer.")


# ----------------------------------------------------------------------
# Onglet 5 : Chercher une salle libre selon créneau et capacité (Bonus)
# ----------------------------------------------------------------------
with tab_recherche:
    st.header("Chercher une salle libre")
    st.caption("Trouvez rapidement les salles disponibles selon vos critères et horaires.")

    with st.form("form_recherche"):
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            r_date = st.date_input("Date souhaitée", value=date(2026, 11, 9), key="rech_date")
            r_participants = st.number_input("Nombre de participants", min_value=1, value=5, step=1, key="rech_parts")
        with col_r2:
            r_debut = st.time_input("Heure de début", value=time(14, 0), key="rech_debut")
            r_fin = st.time_input("Heure de fin", value=time(16, 0), key="rech_fin")

        r_proj = st.checkbox("Projecteur requis", key="rech_proj")
        submit_recherche = st.form_submit_button("Rechercher les salles libres")

    if submit_recherche:
        d_str = r_date.strftime("%Y-%m-%d")
        deb_str = f"{r_debut.hour:02d}:{r_debut.minute:02d}"
        fi_str = f"{r_fin.hour:02d}:{r_fin.minute:02d}"

        try:
            with ouvrir_base() as conn:
                libres = trouver_salles_libres(
                    conn=conn,
                    date_str=d_str,
                    debut_str=deb_str,
                    fin_str=fi_str,
                    participants=r_participants,
                    avec_projecteur=r_proj,
                )

            if libres:
                st.success(f"✅ {len(libres)} salle(s) trouvée(s) pour le créneau {deb_str} - {fi_str} le {d_str} :")
                resultats = [
                    {
                        "Salle": s["nom"],
                        "Capacité": s["capacite"],
                        "Projecteur": "Oui" if s["projecteur"] else "Non",
                    }
                    for s in libres
                ]
                st.dataframe(resultats, use_container_width=True)
            else:
                st.warning("Aucune salle n'est disponible pour ce créneau et ces critères")
        except ValueError as err:
            st.error(f"Paramètres invalides : {err}")