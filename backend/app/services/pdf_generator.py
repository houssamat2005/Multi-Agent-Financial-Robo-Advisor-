"""
Génération de rapports PDF mensuels.
Utilise ReportLab.
"""
import io
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

log = logging.getLogger(__name__)


def generate_portfolio_pdf(
    user_email: str,
    portfolio_name: str,
    capital: float,
    holdings: list[dict],
    recommendation_text: str = "",
    metrics: dict = None,
) -> io.BytesIO:
    """
    Génère un rapport PDF en mémoire pour un portefeuille.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    title_style.alignment = 1  # Center
    h2_style = styles["Heading2"]
    normal_style = styles["Normal"]
    
    # Style personnalisé pour la recommandation
    rec_style = ParagraphStyle(
        "Recommendation",
        parent=styles["Normal"],
        backColor=colors.whitesmoke,
        borderColor=colors.lightgrey,
        borderWidth=1,
        borderPadding=10,
        spaceBefore=10,
        spaceAfter=10,
    )

    story = []

    # ── En-tête ───────────────────────────────────────────────
    story.append(Paragraph(f"Rapport de Portefeuille : {portfolio_name}", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
    story.append(Paragraph(f"Utilisateur : {user_email}", normal_style))
    story.append(Paragraph(f"Capital Total : ${capital:,.2f}", normal_style))
    story.append(Spacer(1, 24))

    # ── Allocation actuelle ───────────────────────────────────
    story.append(Paragraph("Allocation Actuelle", h2_style))
    story.append(Spacer(1, 12))

    if holdings:
        table_data = [["Ticker", "Quantité", "Prix d'Achat", "Valeur Actuelle", "Poids (%)"]]
        for h in holdings:
            table_data.append([
                h.get("ticker", ""),
                f"{h.get('quantity', 0):.4f}",
                f"${h.get('avg_buy_price', 0):.2f}",
                f"${h.get('market_value', 0):.2f}",
                f"{h.get('weight_pct', 0) * 100:.1f}%"
            ])

        t = Table(table_data, colWidths=[80, 80, 100, 100, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Portefeuille vide.", normal_style))
        
    story.append(Spacer(1, 24))

    # ── Métriques (si disponibles) ────────────────────────────
    if metrics:
        story.append(Paragraph("Performances (Backtest)", h2_style))
        story.append(Spacer(1, 12))
        
        m_data = [
            ["Rendement Total", f"{metrics.get('total_return', 0)*100:.2f}%"],
            ["Ratio de Sharpe", f"{metrics.get('sharpe_ratio', 0):.2f}"],
            ["Max Drawdown", f"{metrics.get('max_drawdown', 0)*100:.2f}%"],
            ["Volatilité Annuelle", f"{metrics.get('annual_volatility', 0)*100:.2f}%"],
        ]
        
        mt = Table(m_data, colWidths=[200, 100])
        mt.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
        ]))
        story.append(mt)
        story.append(Spacer(1, 24))

    # ── Recommandation du conseiller IA ────────────────────────
    if recommendation_text:
        story.append(Paragraph("Recommandation du Conseiller IA", h2_style))
        story.append(Spacer(1, 12))
        # Remplacer les retours à la ligne par des balises HTML pour ReportLab
        formatted_text = recommendation_text.replace('\n', '<br/>')
        story.append(Paragraph(formatted_text, rec_style))

    # Génération du PDF
    doc.build(story)
    buffer.seek(0)
    return buffer
