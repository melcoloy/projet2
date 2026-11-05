from pathlib import Path

import base
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parent / "app.py"


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "BASE", tmp_path / "data.db")
    page = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not page.exception
    return page


def test_accueil(page):
    assert "S1" in [salle["nom"] for salle in _salles()]


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
    page.text_input(key="ajout_nom").set_value("S1")
    page.form_submit_button(key="ajouter_salle").click()
    page.run()

    assert any("existe déjà" in erreur.value for erreur in page.error)
    assert len(_salles()) == 2

    page.text_input(key="modif_nom_1").set_value("S2")
    page.form_submit_button(key="enregistrer_salle").click()
    page.run()

    assert any("existe déjà" in erreur.value for erreur in page.error)
    assert _salle_par_id(1)["nom"] == "S1"
    assert _salle_par_id(2)["nom"] == "S2"


def test_modifier_salle(page):
    page.text_input(key="modif_nom_1").set_value("S1 modifiée")
    page.number_input(key="modif_capacite_1").set_value(25)
    page.checkbox(key="modif_projecteur_1").uncheck()
    page.form_submit_button(key="enregistrer_salle").click()
    page.run()

    assert not page.exception
    salle = _salle_par_nom("S1 modifiée")
    assert salle["id"] == 1
    assert salle["capacite"] == 25
    assert salle["projecteur"] == 0


def test_supprimer_salle_supprime_ses_reservations(page):
    page.selectbox(key="salle_a_supprimer").select(1)
    page.button(key="supprimer_salle").click()
    page.run()

    assert not page.exception
    assert _salle_par_id(1) is None
    with base.ouvrir_base() as conn:
        reservations = conn.execute(
            "SELECT * FROM reservations WHERE salle_id = 1"
        ).fetchall()
    assert reservations == []


def _salles():
    with base.ouvrir_base() as conn:
        return conn.execute("SELECT * FROM salles").fetchall()


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
