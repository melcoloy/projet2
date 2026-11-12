-- Schéma de la base : Réservation de salles. Vous pouvez le modifier.
CREATE TABLE IF NOT EXISTS salles (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    capacite INTEGER NOT NULL,
    projecteur INTEGER NOT NULL DEFAULT 0,
    type TEXT NOT NULL DEFAULT 'Salle de cours'
);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY,
    salle_id INTEGER NOT NULL REFERENCES salles(id) ON DELETE CASCADE,
    personne TEXT NOT NULL,
    date TEXT NOT NULL,
    debut TEXT NOT NULL,
    fin TEXT NOT NULL,
    participants INTEGER NOT NULL,
    recurrence_id TEXT DEFAULT NULL
);

-- Données d'exemple, chargées à la création de data.db. Le 9 novembre 2026 est un lundi.
INSERT INTO salles (id, nom, capacite, projecteur, type) VALUES
(1, 'S1', 20, 1, 'Salle de cours'),
(2, 'S2', 8, 0, 'Salle de réunion');

INSERT INTO reservations (id, salle_id, personne, date, debut, fin, participants, recurrence_id) VALUES
-- Réservations pour la salle S1 (capacité 20, projecteur 1)
(1, 1, 'Alice', '2026-11-09', '10:00', '12:00', 12, NULL),
(2, 1, 'Pr. Dupont', '2026-11-10', '09:00', '11:30', 18, NULL),
(3, 1, 'Clara', '2026-11-10', '14:00', '16:30', 15, NULL),
(4, 1, 'David', '2026-11-11', '10:00', '12:00', 10, NULL),
(5, 1, 'Équipe Robotique', '2026-11-11', '14:30', '17:30', 16, NULL),
(6, 1, 'Emma', '2026-11-12', '08:30', '10:30', 8, NULL),
(7, 1, 'Réunion Départementale', '2026-11-12', '14:00', '17:00', 20, NULL),
(8, 1, 'Marc', '2026-11-13', '09:30', '11:30', 14, NULL),
(9, 1, 'Sophie', '2026-11-13', '14:00', '16:00', 12, NULL),

-- Réservations pour la salle S2 (capacité 8, projecteur 0)
(10, 2, 'Julien', '2026-11-10', '10:00', '12:00', 4, NULL),
(11, 2, 'Lucas', '2026-11-10', '14:30', '16:30', 6, NULL),
(12, 2, 'Léa', '2026-11-11', '09:00', '11:00', 7, NULL),
(13, 2, 'Antoine', '2026-11-11', '15:00', '17:00', 5, NULL),
(14, 2, 'Thomas', '2026-11-12', '10:30', '12:30', 8, NULL),
(15, 2, 'Chloé', '2026-11-12', '14:00', '15:30', 4, NULL),
(16, 2, 'Maxime', '2026-11-13', '09:00', '11:00', 5, NULL),
(17, 2, 'Camille', '2026-11-13', '14:00', '16:00', 3, NULL);
