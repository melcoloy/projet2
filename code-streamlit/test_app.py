from datetime import date, time
from pathlib import Path

import base
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parent / "app.py"


@pytest.fixture
def page(tmp_path, monkeypatch):
    """Base neuve réduite au scénario à vérifier : S1 de capacité 20,
    réservée le lundi 9 novembre 2026 de 10 h à 12 h."""
    monkeypatch.setattr(base, "BASE", tmp_path / "data.db")
    with base.ouvrir_base() as conn:
        conn.execute("DELETE FROM reservations")
        conn.execute(
            "INSERT INTO reservations (id, salle_id, personne, date, debut, fin, participants) "
            "VALUES (1, 1, 'Alice', '2026-11-09', '10:00', '12:00', 12)"
        )
    page = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not page.exception
    return page


def test_accueil(page):
    assert page.header[0].value == "Salles"
    noms = page.dataframe[0].value["Nom"].tolist()
    assert "S1" in noms


def test_ajouter_salle(page):
    page.text_input(key="ajout_nom").set_value("S3")
    page.number_input(key="ajout_capacite").set_value(30)
    page.checkbox(key="ajout_projecteur").check()
    page.form_submit_button(key="ajouter_salle").click()
    page.run()

    assert not page.exception
    salle = _salle_par_nom("S3")
    assert salle["capacite"] == 30
    assert salle["projecteur"] == 1


def test_ajouter_salle_sans_nom(page):
    page.form_submit_button(key="ajouter_salle").click()
    page.run()

    assert page.error
    assert len(_salles()) == 2


def test_refuse_nom_de_salle_deja_utilise(page):
    page.text_input(key="ajout_nom").set_value("s1")
    page.form_submit_button(key="ajouter_salle").click()
    page.run()

    assert any("existe déjà" in erreur.value for erreur in page.error)
    assert len(_salles()) == 2

    id_s1 = _id_par_nom("S1")
    page.text_input(key=f"modif_nom_{id_s1}").set_value("S2")
    page.form_submit_button(key="enregistrer_salle").click()
    page.run()

    assert any("existe déjà" in erreur.value for erreur in page.error)
    assert _salle_par_id(id_s1)["nom"] == "S1"
    assert _salle_par_nom("S2")["nom"] == "S2"


def test_modifier_salle(page):
    id_s1 = _id_par_nom("S1")
    page.text_input(key=f"modif_nom_{id_s1}").set_value("S1 modifiée")
    page.number_input(key=f"modif_capacite_{id_s1}").set_value(25)
    page.checkbox(key=f"modif_projecteur_{id_s1}").uncheck()
    page.form_submit_button(key="enregistrer_salle").click()
    page.run()

    assert not page.exception
    salle = _salle_par_nom("S1 modifiée")
    assert salle["id"] == id_s1
    assert salle["capacite"] == 25
    assert salle["projecteur"] == 0


def test_modifier_salle_sans_nom(page):
    id_s1 = _id_par_nom("S1")
    page.text_input(key=f"modif_nom_{id_s1}").set_value("   ")
    page.form_submit_button(key="enregistrer_salle").click()
    page.run()

    assert page.error
    assert _salle_par_id(id_s1)["nom"] == "S1"


def test_modifier_salle_change_seulement_la_casse(page):
    id_s1 = _id_par_nom("S1")
    page.text_input(key=f"modif_nom_{id_s1}").set_value("s1")
    page.form_submit_button(key="enregistrer_salle").click()
    page.run()

    assert not page.exception
    assert not page.error
    assert _salle_par_id(id_s1)["nom"] == "s1"
    assert len(_salles()) == 2


def test_refuse_nom_de_salle_avec_accents_et_casse(page):
    page.text_input(key="ajout_nom").set_value("École")
    page.form_submit_button(key="ajouter_salle").click()
    page.run()

    assert not page.exception
    assert _salle_par_nom("École")["nom"] == "École"

    page.text_input(key="ajout_nom").set_value("école")
    page.form_submit_button(key="ajouter_salle").click()
    page.run()

    assert any("existe déjà" in erreur.value for erreur in page.error)
    noms = [salle["nom"] for salle in _salles() if salle["nom"].casefold() == "école"]
    assert noms == ["École"]


def test_supprimer_salle_sans_confirmation(page):
    id_s1 = _id_par_nom("S1")
    page.selectbox(key="salle_a_supprimer").select(id_s1)
    page.run()
    page.form_submit_button(key="supprimer_salle").click()
    page.run()

    assert any("confirmer" in erreur.value for erreur in page.error)
    assert _salle_par_id(id_s1) is not None


def test_supprimer_salle_supprime_ses_reservations(page):
    id_s1 = _id_par_nom("S1")
    page.selectbox(key="salle_a_supprimer").select(id_s1)
    page.run()
    page.checkbox(key=f"confirmer_suppression_{id_s1}").check()
    page.form_submit_button(key="supprimer_salle").click()
    page.run()

    assert not page.exception
    assert _salle_par_id(id_s1) is None
    with base.ouvrir_base() as conn:
        reservations = conn.execute(
            "SELECT * FROM reservations WHERE salle_id = ?", [id_s1]
        ).fetchall()
    assert reservations == []


@pytest.mark.parametrize(
    "date_reservation, debut, fin, participants, attendu",
    [
        (date(2026, 11, 9), time(11, 0), time(13, 0), 5, "déjà réservée"),
        (date(2026, 11, 9), time(12, 0), time(13, 0), 5, None),
        (date(2026, 11, 9), time(14, 0), time(15, 0), 25, "participants"),
        (date(2026, 11, 9), time(7, 30), time(9, 0), 5, "8 h"),
        (date(2026, 11, 10), time(14, 0), time(14, 20), 5, "30 minutes"),
        (date(2026, 11, 10), time(8, 0), time(13, 0), 5, "4 heures"),
    ],
    ids=[
        "lundi-11h-13h-chevauchement",
        "lundi-12h-13h-acceptee",
        "lundi-14h-15h-capacite",
        "lundi-7h30-9h-avant-8h",
        "mardi-14h-14h20-moins-30min",
        "mardi-8h-13h-plus-4h",
    ],
)
def test_reserver_les_six_cas_du_tableau(
    page, date_reservation, debut, fin, participants, attendu
):
    id_s1 = _id_par_nom("S1")
    page.selectbox(key="reservation_salle").select(id_s1)
    page.text_input(key="reservation_personne").set_value("Bob")
    page.date_input(key="reservation_date").set_value(date_reservation)
    page.time_input(key="reservation_debut").set_value(debut)
    page.time_input(key="reservation_fin").set_value(fin)
    page.number_input(key="reservation_participants").set_value(participants)
    page.form_submit_button(key="reserver_salle").click()
    page.run()

    assert not page.exception
    if attendu is None:
        assert any(succes.value for succes in page.success)
        assert len(_reservations()) == 2
    else:
        assert any(attendu in erreur.value for erreur in page.error)
        assert len(_reservations()) == 1


def test_reserver_sans_personne(page):
    id_s1 = _id_par_nom("S1")
    page.selectbox(key="reservation_salle").select(id_s1)
    page.date_input(key="reservation_date").set_value(date(2026, 11, 10))
    page.form_submit_button(key="reserver_salle").click()
    page.run()

    assert not page.exception
    assert any("obligatoire" in erreur.value for erreur in page.error)
    assert len(_reservations()) == 1


@pytest.mark.parametrize(
    "nom_salle, date_reservation",
    [("S2", date(2026, 11, 9)), ("S1", date(2026, 11, 10))],
    ids=["autre-salle", "autre-date"],
)
def test_reserver_salle_ou_date_differente(page, nom_salle, date_reservation):
    page.selectbox(key="reservation_salle").select(_id_par_nom(nom_salle))
    page.text_input(key="reservation_personne").set_value("Bob")
    page.date_input(key="reservation_date").set_value(date_reservation)
    page.time_input(key="reservation_debut").set_value(time(10, 0))
    page.time_input(key="reservation_fin").set_value(time(12, 0))
    page.number_input(key="reservation_participants").set_value(5)
    page.form_submit_button(key="reserver_salle").click()
    page.run()

    assert not page.exception
    assert any(succes.value for succes in page.success)
    assert len(_reservations()) == 2


def test_liste_des_reservations(page):
    textes = [str(element.value) for element in page.markdown]

    for attendu in ("**Salle**", "S1", "Alice", "2026-11-09", "10:00", "12:00", "12"):
        assert attendu in textes
    assert page.button(key="annuler_1").label == "Annuler"


def test_annuler_reservation(page):
    page.button(key="annuler_1").click()
    page.run()

    assert len(_reservations()) == 1
    page.button(key="confirmer_annulation").click()
    page.run()

    assert not page.exception
    assert _reservations() == []
    assert any("Aucune réservation" in info.value for info in page.info)
    assert any("annulée" in succes.value for succes in page.success)


def test_annuler_une_seule_reservation(page):
    with base.ouvrir_base() as conn:
        conn.execute(
            "INSERT INTO reservations (id, salle_id, personne, date, debut, fin, participants) "
            "VALUES (2, 1, 'Bob', '2026-11-09', '13:00', '14:00', 5)"
        )
    page.run()

    page.button(key="annuler_1").click()
    page.run()
    assert len(_reservations()) == 2

    page.button(key="confirmer_annulation").click()
    page.run()

    assert not page.exception
    restantes = _reservations()
    assert [reservation["id"] for reservation in restantes] == [2]
    assert restantes[0]["personne"] == "Bob"


def _salles():
    with base.ouvrir_base() as conn:
        return conn.execute("SELECT * FROM salles").fetchall()


def _reservations():
    with base.ouvrir_base() as conn:
        return conn.execute("SELECT * FROM reservations").fetchall()


def _salle_par_nom(nom):
    with base.ouvrir_base() as conn:
        salle = conn.execute(
            "SELECT * FROM salles WHERE nom = ?", [nom]
        ).fetchone()
    assert salle is not None
    return salle


def _salle_par_id(salle_id):
    with base.ouvrir_base() as conn:
        return conn.execute(
            "SELECT * FROM salles WHERE id = ?", [salle_id]
        ).fetchone()


def _id_par_nom(nom):
    return _salle_par_nom(nom)["id"]
