import html
import io
import sqlite3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from database import NOM_BASE


def charger_donnees():
    """Charge les données SQLite dans un DataFrame."""
    connexion = sqlite3.connect(NOM_BASE)
    try:
        return pd.read_sql_query("SELECT * FROM donnees", connexion)
    finally:
        connexion.close()


def tableau_comparatif(df):
    """Présente les indicateurs en colonnes et les entreprises en lignes."""
    return df.pivot_table(
        index="entreprise",
        columns="indicateur",
        values="valeur",
    )


def calculer_resume(df, indicateur):
    """Calcule les valeurs extrêmes et la moyenne d'un indicateur."""
    valeurs = df.loc[df["indicateur"] == indicateur, ["entreprise", "valeur"]]
    if valeurs.empty:
        raise ValueError(f"Aucune donnée disponible pour « {indicateur} ».")

    valeurs = valeurs.copy()
    valeurs["valeur"] = pd.to_numeric(valeurs["valeur"])
    ligne_max = valeurs.loc[valeurs["valeur"].idxmax()]
    ligne_min = valeurs.loc[valeurs["valeur"].idxmin()]

    return {
        "indicateur": str(indicateur),
        "meilleur": str(ligne_max["entreprise"]),
        "valeur_max": float(ligne_max["valeur"]),
        "plus_bas": str(ligne_min["entreprise"]),
        "valeur_min": float(ligne_min["valeur"]),
        "moyenne": float(round(valeurs["valeur"].mean(), 2)),
    }


def faire_graphique(df, indicateur, chemin):
    """Enregistre un graphique en barres au format PNG."""
    valeurs = df.loc[df["indicateur"] == indicateur, ["entreprise", "valeur"]]
    if valeurs.empty:
        raise ValueError(f"Aucune donnée disponible pour « {indicateur} ».")

    figure, axe = plt.subplots(figsize=(8, 4.5))
    axe.bar(valeurs["entreprise"], valeurs["valeur"], color="#1F4E9C")
    axe.set_title(indicateur)
    axe.set_ylabel(indicateur)
    figure.tight_layout()
    figure.savefig(chemin, format="png")
    plt.close(figure)


def faire_graphique_repartition(comptage, titre, chemin):
    """Enregistre la répartition des réponses d'une question en PNG."""
    figure, axe = plt.subplots(figsize=(8, 4.5))
    comptage.sort_values().plot.barh(ax=axe, color="#2563EB")
    axe.set_title(titre)
    axe.set_xlabel("Nombre de réponses")
    axe.set_ylabel("")
    figure.tight_layout()
    figure.savefig(chemin, format="png")
    plt.close(figure)


def creer_rapport_pdf(
    titre, sujet, resume, sources, details=None, chemin_graphique=None, client=None
):
    """Crée un rapport PDF réutilisable avec synthèse, graphique et sources."""
    contenu = io.BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#17233b"),
            alignment=0,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#334155"),
            splitLongWords=1,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportSource",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569"),
            splitLongWords=1,
            spaceAfter=5,
        )
    )

    def pied_de_page(canevas, document):
        canevas.saveState()
        canevas.setStrokeColor(colors.HexColor("#dbe3ef"))
        canevas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
        canevas.setFont("Helvetica", 8)
        canevas.setFillColor(colors.HexColor("#64748b"))
        canevas.drawString(20 * mm, 10 * mm, "MarketRadar AI · Rapport à vérifier")
        canevas.drawRightString(190 * mm, 10 * mm, str(document.page))
        canevas.restoreState()

    rapport = SimpleDocTemplate(
        contenu,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=f"{titre} — MarketRadar AI",
        author="MarketRadar AI",
    )
    elements = [
        Paragraph(html.escape(str(titre)), styles["ReportTitle"]),
        Paragraph(html.escape(str(sujet)), styles["ReportBody"]),
    ]
    if client and str(client).strip():
        elements.append(
            Paragraph(
                f"Client : {html.escape(str(client).strip())}",
                styles["ReportBody"],
            )
        )
    elements.extend([Spacer(1, 8), Paragraph("Synthèse", styles["Heading2"])])
    for ligne in str(resume).splitlines() or [""]:
        elements.append(Paragraph(html.escape(ligne), styles["ReportBody"]))

    for detail in details or []:
        elements.append(Paragraph(html.escape(str(detail)), styles["ReportBody"]))

    if chemin_graphique:
        elements.extend(
            [
                Spacer(1, 8),
                Paragraph("Visualisation", styles["Heading2"]),
                Image(
                    chemin_graphique,
                    width=165 * mm,
                    height=90 * mm,
                    kind="proportional",
                ),
            ]
        )

    elements.append(Paragraph("Sources", styles["Heading2"]))
    for source in sources or ["Aucune source fournie"]:
        elements.append(Paragraph(html.escape(str(source)), styles["ReportSource"]))

    rapport.build(elements, onFirstPage=pied_de_page, onLaterPages=pied_de_page)
    return contenu.getvalue()


def creer_pdf(texte, chemin_graphique, sources):
    """Compatibilité avec l'ancien générateur de rapports."""
    return creer_rapport_pdf(
        "Rapport comparatif",
        "Analyse d'indicateurs",
        texte,
        sources,
        chemin_graphique=chemin_graphique,
    )


if __name__ == "__main__":
    donnees = charger_donnees()
    print(tableau_comparatif(donnees))
    resume = calculer_resume(donnees, "Clients (millions)")
    print(resume)
    faire_graphique(donnees, "Clients (millions)", "graphique.png")
    from ia import resume_sans_ia

    pdf = creer_pdf(
        resume_sans_ia(resume),
        "graphique.png",
        sorted(donnees["source"].dropna().unique()),
    )
    with open("rapport.pdf", "wb") as fichier_pdf:
        fichier_pdf.write(pdf)
