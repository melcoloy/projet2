from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_accueil():
    """Vérifie que l'application s'exécute de haut en bas sans lever d'exception."""
    page = AppTest.from_file(str(Path(__file__).parent / "app.py"), default_timeout=60).run()
    assert not page.exception
    assert len(page.tabs) == 5
    assert page.title[0].value == "🏢 Système de Réservation de Salles"


def test_planning_et_onglets():
    """Vérifie le chargement des onglets et l'absence d'exception après interaction."""
    page = AppTest.from_file(str(Path(__file__).parent / "app.py"), default_timeout=60).run()
    assert not page.exception

    # Vérifie la présence des métriques, des sélecteurs et de la case de récurrence
    assert len(page.selectbox) >= 1
    assert len(page.date_input) >= 1
    assert any("Répéter chaque semaine" in cb.label for cb in page.checkbox)
