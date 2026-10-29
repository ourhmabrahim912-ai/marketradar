import os
import tempfile

import pandas as pd
import streamlit as st

from analyse import creer_rapport_pdf, faire_graphique_repartition


st.markdown(
    """
    <style>
    .stApp { background: #f5f7fb; }
    .block-container { max-width: 1280px; padding-top: 2.25rem; padding-bottom: 4rem; }
    [data-testid="stSidebar"] { background: #f0f4fa; }
    .survey-hero {
        padding: 2rem 2.3rem;
        margin-bottom: 1.5rem;
        border: 1px solid #dce6f8;
        border-radius: 22px;
        background: linear-gradient(120deg, #ffffff 0%, #eef4ff 100%);
    }
    .survey-hero span {
        color: #2563eb;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .survey-hero h1 { margin: 0.45rem 0 0.35rem; color: #17233b; }
    .survey-hero p { color: #64748b; font-size: 1.05rem; margin: 0; }
    [data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        background: #fff;
    }
    [data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 14px; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="survey-hero">
        <span>Analyse des réponses</span>
        <h1>Mode Sondage</h1>
        <p>Importez les réponses, choisissez une question et repérez les tendances.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.subheader("Importer les réponses")
st.caption("Le fichier CSV doit contenir une colonne par question et une ligne par réponse.")
fichier = st.file_uploader("Choisir un fichier CSV", type="csv")

if fichier is not None:
    try:
        donnees = pd.read_csv(fichier)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as erreur:
        st.error(f"Impossible de lire le fichier CSV : {erreur}")
    else:
        if donnees.empty or len(donnees.columns) == 0:
            st.error("Le fichier CSV ne contient aucune réponse.")
        else:
            resume = st.columns(3)
            resume[0].metric("Réponses", len(donnees))
            resume[1].metric("Questions", len(donnees.columns))
            resume[2].metric("Réponses renseignées", int(donnees.notna().sum().sum()))
            st.subheader("Aperçu du fichier")
            st.dataframe(donnees.head(), use_container_width=True)

            st.subheader("Résultats par question")
            question = st.selectbox("Choisir une question", list(donnees.columns))
            comptage = donnees[question].dropna().value_counts()
            total = int(comptage.sum())
            if total == 0:
                st.info("Aucune réponse disponible pour cette question.")
            else:
                pourcentages = (comptage / total * 100).round(1)
                st.bar_chart(comptage, use_container_width=True)
                tableau_resultats = pd.DataFrame(
                    {
                        "Réponses": comptage,
                        "Pourcentage (%)": pourcentages,
                    }
                )
                st.dataframe(tableau_resultats, use_container_width=True)

                reponse_frequente = str(comptage.idxmax())
                pourcentage_frequent = float(pourcentages.loc[comptage.idxmax()])
                st.success(
                    f"Pour la question « {question} », la réponse la plus fréquente "
                    f"est « {reponse_frequente} » ({pourcentage_frequent:.1f} % "
                    f"des {total} réponses)."
                )
                st.caption("Source : fichier importé " + fichier.name)
                st.markdown("#### Préparer un rapport")
                st.caption(
                    "Relisez les résultats avant de créer le PDF réutilisable "
                    "avec le résumé, le graphique et la référence du fichier."
                )
                client_rapport = st.text_input(
                    "Client du rapport (facultatif)", key="sondage_client"
                )
                resume_valide = st.checkbox(
                    "J'ai vérifié les résultats et le fichier source",
                    key="sondage_resume_valide",
                )
                if resume_valide:
                    resume = (
                        f"Pour la question « {question} », la réponse la plus "
                        f"fréquente est « {reponse_frequente} » "
                        f"({pourcentage_frequent:.1f} % des {total} réponses)."
                    )
                    with tempfile.NamedTemporaryFile(
                        suffix=".png", delete=False
                    ) as image_temporaire:
                        chemin_graphique = image_temporaire.name
                    try:
                        faire_graphique_repartition(
                            comptage, f"Réponses à : {question}", chemin_graphique
                        )
                        rapport_pdf = creer_rapport_pdf(
                            "Rapport sondage",
                            f"Résultats pour la question : {question}",
                            resume,
                            [f"Fichier importé : {fichier.name}"],
                            details=[
                                f"Réponses renseignées pour cette question : {total}",
                                "Répartition : "
                                + "; ".join(
                                    f"{reponse} : {int(comptage.loc[reponse])} "
                                    f"({pourcentages.loc[reponse]:.1f} %)"
                                    for reponse in comptage.index
                                ),
                            ],
                            chemin_graphique=chemin_graphique,
                            client=client_rapport,
                        )
                        st.download_button(
                            "Télécharger le rapport PDF",
                            data=rapport_pdf,
                            file_name="rapport_sondage.pdf",
                            mime="application/pdf",
                        )
                    finally:
                        if os.path.exists(chemin_graphique):
                            os.remove(chemin_graphique)