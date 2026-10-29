import sqlite3


NOM_BASE = "marketradar.db"


def connecter():
    """Ouvre une connexion à la base SQLite."""
    return sqlite3.connect(NOM_BASE)


def creer_table():
    """Crée la table des données si elle n'existe pas."""
    connexion = connecter()
    try:
        connexion.execute(
            """
            CREATE TABLE IF NOT EXISTS donnees (
                entreprise TEXT NOT NULL,
                indicateur TEXT NOT NULL,
                valeur REAL NOT NULL,
                source TEXT NOT NULL CHECK (length(trim(source)) > 0)
            )
            """
        )
        connexion.commit()
    finally:
        connexion.close()


def remplir_donnees_test():
    """Remplace les données par les six lignes fictives de démonstration."""
    lignes = [
        ("Telecom A", "Clients (millions)", 18.5, "Données fictives"),
        ("Telecom B", "Clients (millions)", 12.1, "Données fictives"),
        ("Telecom C", "Clients (millions)", 9.4, "Données fictives"),
        ("Telecom A", "Prix moyen (MAD)", 120, "Données fictives"),
        ("Telecom B", "Prix moyen (MAD)", 110, "Données fictives"),
        ("Telecom C", "Prix moyen (MAD)", 95, "Données fictives"),
    ]
    connexion = connecter()
    try:
        connexion.execute("DELETE FROM donnees")
        connexion.executemany(
            """
            INSERT INTO donnees (entreprise, indicateur, valeur, source)
            VALUES (?, ?, ?, ?)
            """,
            lignes,
        )
        connexion.commit()
    finally:
        connexion.close()


def afficher_donnees():
    """Affiche les lignes présentes dans la base."""
    connexion = connecter()
    try:
        for ligne in connexion.execute(
            "SELECT entreprise, indicateur, valeur, source FROM donnees"
        ):
            print(ligne)
    finally:
        connexion.close()


if __name__ == "__main__":
    # Exécuter ce fichier remet la base à zéro.
    creer_table()
    remplir_donnees_test()
    afficher_donnees()
