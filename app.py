import os
import tempfile

import pandas as pd
import streamlit as st

from analyse import (
    calculer_resume,
    charger_donnees,
    creer_rapport_pdf,
    faire_graphique,
    tableau_comparatif,
)
from database import connecter, creer_table
from ia import rediger_resume
import sqlite3
con = sqlite3.connect("marketradar.db")
con.execute("CREATE TABLE IF NOT EXISTS donnees (entreprise TEXT, indicateur TEXT, valeur REAL, source TEXT)")
if con.execute("SELECT COUNT(*) FROM donnees").fetchone()[0] == 0:
    lignes = [
        ("Telecom A", "Clients (millions)", 18.5, "Données fictives"),
        ("Telecom B", "Clients (millions)", 12.1, "Données fictives"),
        ("Telecom C", "Clients (millions)", 9.4, "Données fictives"),
        ("Telecom A", "Prix moyen (MAD)", 120, "Données fictives"),
        ("Telecom B", "Prix moyen (MAD)", 110, "Données fictives"),
        ("Telecom C", "Prix moyen (MAD)", 95, "Données fictives"),
    ]
    con.executemany("INSERT INTO donnees VALUES (?,?,?,?)", lignes)
con.commit()
con.close()

st.set_page_config(
    page_title="MarketRadar AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    :root {
        --ink: #17233b;
        --muted: #64748b;
        --blue: #2563eb;
        --line: #e2e8f0;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 85% 0%, #e8efff 0, transparent 34rem),
            #f5f7fb;
        color: var(--ink);
    }
    .block-container {
        max-width: 1280px;
        padding-top: 2.25rem;
        padding-bottom: 4rem;
    }
    [data-testid="stSidebar"] {
        background: #f0f4fa;
        border-right: 1px solid var(--line);
    }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.025em; }
    h2 { margin-top: 1.75rem; }
    .hero {
        padding: 2.1rem 2.3rem;
        margin-bottom: 1.5rem;
        border: 1px solid #dce6f8;
        border-radius: 22px;
        background: linear-gradient(120deg, #ffffff 0%, #eef4ff 100%);
        box-shadow: 0 12px 32px rgba(37, 69, 125, 0.06);
    }
    .hero-eyebrow {
        color: var(--blue);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .hero h1 {
        margin: 0.45rem 0 0.35rem;
        font-size: clamp(2rem, 4vw, 2.8rem);
    }
    .hero p { color: var(--muted); font-size: 1.05rem; margin: 0; }
    .section-kicker {
        color: var(--blue);
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: -0.8rem;
    }
    [data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid var(--line);
        border-radius: 14px;
        background: #fff;
        box-shadow: 0 4px 14px rgba(31, 51, 82, 0.04);
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 14px;
        overflow: hidden;
    }
    .stButton > button, .stDownloadButton > button {
        background-color: #1f4e9c;
        color: white;
        border: 0;
        border-radius: 10px;
        min-height: 2.7rem;
        font-weight: 600;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #173d7c;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="hero">
        <div class="hero-eyebrow">Mode 1 sur 3 · Benchmark</div>
        <h1>MarketRadar AI</h1>
        <p>Comparez les entreprises, vérifiez les résultats et préparez un rapport PDF partagé.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("### Paramètres")
st.sidebar.caption("L'IA est facultative. Sans clé, un résumé automatique est utilisé.")
cle_api = st.sidebar.text_input("Clé API Anthropic (facultative)", type="password")
if not cle_api:
    cle_api = os.environ.get("ANTHROPIC_API_KEY")

creer_table()

st.markdown(
    '<div class="section-kicker">Étape 1 · Données</div>',
    unsafe_allow_html=True,
)
st.subheader("Importer des données")
st.caption(
    "Ajoutez un CSV pour compléter la base. Les colonnes requises sont "
    "`entreprise`, `indicateur`, `valeur` et `source`."
)
fichier_csv = st.file_uploader(
    "Choisir un fichier CSV",
    type="csv",
    help="Chaque ligne doit avoir une valeur numérique et une source non vide.",
)

if fichier_csv is not None and st.button("Ajouter à la base"):
    try:
        nouveau = pd.read_csv(fichier_csv)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as erreur:
        st.error(f"Impossible de lire le fichier CSV : {erreur}")
    else:
        colonnes_requises = ["entreprise", "indicateur", "valeur", "source"]
        if not set(colonnes_requises).issubset(nouveau.columns):
            st.error(
                "Il faut les quatre colonnes : entreprise, indicateur, valeur, source."
            )
        elif nouveau.empty:
            st.error("Le fichier CSV ne contient aucune ligne de données.")
        else:
            nouveau = nouveau[colonnes_requises].copy()
            nouveau["valeur"] = pd.to_numeric(nouveau["valeur"], errors="coerce")
            if nouveau["valeur"].isna().any():
                st.error("La colonne valeur doit contenir uniquement des nombres.")
            else:
                sources = nouveau["source"].fillna("").astype(str).str.strip()
                if sources.eq("").any():
                    st.error("Chaque ligne doit avoir une source.")
                else:
                    nouveau["source"] = sources
                    champs_vides = (
                        nouveau["entreprise"].isna()
                        | nouveau["indicateur"].isna()
                        | nouveau["entreprise"].astype(str).str.strip().eq("")
                        | nouveau["indicateur"].astype(str).str.strip().eq("")
                    )
                    if champs_vides.any():
                        st.error("Chaque ligne doit avoir une entreprise et un indicateur.")
                    else:
                        connexion = connecter()
                        try:
                            nouveau.to_sql(
                                "donnees",
                                connexion,
                                if_exists="append",
                                index=False,
                            )
                            connexion.commit()
                        except Exception as erreur:
                            connexion.rollback()
                            st.error(f"Impossible d'ajouter les données : {erreur}")
                        else:
                            for cle in (
                                "resume",
                                "texte",
                                "indicateur",
                                "resume_valide",
                                "texte_modifie",
                            ):
                                st.session_state.pop(cle, None)
                            st.success(f"{len(nouveau)} lignes ajoutées.")
                            st.rerun()
                        finally:
                            connexion.close()

donnees = charger_donnees()
st.markdown(
    '<div class="section-kicker">Étape 2 · Vue d’ensemble</div>',
    unsafe_allow_html=True,
)
st.subheader("Données comparatives")
if donnees.empty:
    st.info(
        "Aucune donnée n'est disponible. Importez un CSV ou lancez "
        "`python database.py` pour charger les données de démonstration."
    )
else:
    tableau = tableau_comparatif(donnees)
    mesures = st.columns(3)
    mesures[0].metric("Entreprises", int(donnees["entreprise"].nunique()))
    mesures[1].metric("Indicateurs", int(donnees["indicateur"].nunique()))
    mesures[2].metric("Observations", len(donnees))

    st.dataframe(tableau, use_container_width=True)

    st.markdown(
        '<div class="section-kicker">Étape 3 · Analyse</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Comparer un indicateur")
    st.caption(
        "Choisissez une mesure pour comparer les entreprises et calculer "
        "les valeurs extrêmes ainsi que la moyenne."
    )
    indicateurs = list(tableau.columns)
    indicateur_choisi = st.selectbox("Choisir un indicateur", indicateurs)
    if st.button("Générer l'analyse"):
        resume = calculer_resume(donnees, indicateur_choisi)
        st.session_state["indicateur"] = indicateur_choisi
        st.session_state["resume"] = resume
        st.session_state["texte"] = rediger_resume(resume, cle_api)
        st.session_state["resume_valide"] = False
        st.session_state.pop("texte_modifie", None)

    if "resume" in st.session_state and "texte" in st.session_state:
        resume = st.session_state["resume"]
        indicateur_resume = st.session_state["indicateur"]
        st.markdown("#### Résultats — " + indicateur_resume)
        resultats = st.columns(3)
        resultats[0].metric("Valeur la plus élevée", resume["valeur_max"])
        resultats[0].caption(f"Entreprise : {resume['meilleur']}")
        resultats[1].metric("Valeur la plus faible", resume["valeur_min"])
        resultats[1].caption(f"Entreprise : {resume['plus_bas']}")
        resultats[2].metric("Moyenne", resume["moyenne"])
        st.bar_chart(tableau[indicateur_resume], use_container_width=True)
        with st.expander("Afficher le détail des calculs"):
            st.caption("Ces chiffres sont calculés par Python à partir des données importées.")
            st.json(resume)

        st.markdown(
            '<div class="section-kicker">Étape 4 · Validation</div>',
            unsafe_allow_html=True,
        )
        st.subheader("Relire avant de partager")
        st.caption(
            "Vérifiez les chiffres, le texte et les sources. Vous pouvez corriger "
            "le résumé avant de produire le PDF."
        )
        texte_corrige = st.text_area(
            "Résumé à inclure dans le rapport",
            value=st.session_state["texte"],
            key="texte_modifie",
            height=130,
        )
        sources = sorted(donnees["source"].dropna().astype(str).unique())
        st.caption("Sources : " + ", ".join(sources))
        client_rapport = st.text_input(
            "Client du rapport (facultatif)", key="benchmark_client"
        )
        resume_valide = st.checkbox(
            "J'ai vérifié les chiffres, le résumé et les sources",
            key="resume_valide",
        )

        if resume_valide:
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as image_temporaire:
                chemin_graphique = image_temporaire.name
            try:
                faire_graphique(donnees, indicateur_resume, chemin_graphique)
                rapport_pdf = creer_rapport_pdf(
                    "Rapport benchmark",
                    f"Comparaison de l'indicateur : {indicateur_resume}",
                    texte_corrige,
                    sources,
                    details=[
                        f"Entreprises comparées : {donnees['entreprise'].nunique()}",
                        f"Observations utilisées : {len(donnees[donnees['indicateur'] == indicateur_resume])}",
                    ],
                    chemin_graphique=chemin_graphique,
                    client=client_rapport,
                )
                st.download_button(
                    "Télécharger le rapport PDF",
                    data=rapport_pdf,
                    file_name="rapport.pdf",
                    mime="application/pdf",
                )
            finally:
                if os.path.exists(chemin_graphique):
                    os.remove(chemin_graphique)
