from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import tempfile

def create_pie_chart_for_pdf(data_dict, title):
    """Create pie chart image for PDF"""
    if not data_dict:
        return None
    
    labels = list(data_dict.keys())
    values = list(data_dict.values())
    
    # Filter out zero values
    nonzero_indices = [i for i, v in enumerate(values) if v > 0]
    labels = [labels[i] for i in nonzero_indices]
    values = [values[i] for i in nonzero_indices]
    
    if not values:
        return None
    
    # Create figure with specific size
    fig, ax = plt.subplots(figsize=(4, 3), dpi=150)
    
    # Use Set3 palette
    colors_list = sns.color_palette('Set3', len(labels))
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors_list,
        startangle=90,
        wedgeprops=dict(width=0.5, edgecolor='white', linewidth=0.5),
        autopct='',
        pctdistance=0.85
    )
    
    # Add legend
    percentages = [(v/sum(values))*100 for v in values]
    legend_labels = [f"{label[:15]} ({pct:.1f}%)" for label, pct in zip(labels, percentages)]
    
    ax.legend(
        wedges,
        legend_labels,
        title=title[:20],
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=6,
        title_fontsize=7
    )
    
    ax.set_title(title, fontsize=9, fontweight='bold', pad=10)
    ax.axis('equal')
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    plt.tight_layout()
    plt.savefig(temp_file.name, dpi=150, bbox_inches='tight', transparent=False)
    plt.close(fig)
    
    return temp_file.name

def create_portfolio_pdf_report(portfolio_data):
    """Create professional PDF report without emojis"""
    buffer = BytesIO()
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles without emojis
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=15,
        alignment=1  # Center alignment
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=8
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        spaceAfter=5
    )
    
    # Build content
    content = []
    
    # Title
    content.append(Paragraph("Portfolio Health Report", title_style))
    content.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M')}", 
                           ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=8, alignment=1)))
    content.append(Spacer(1, 20))
    
    # Portfolio Summary
    content.append(Paragraph("Portfolio Summary", section_style))
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Investment', f"₹{portfolio_data['total_investment']:,.0f}"],
        ['Current Value', f"₹{portfolio_data['total_value']:,.0f}"],
        ['Total Gain/Loss', f"₹{portfolio_data['total_gain_loss']:,.0f}"],
        ['Overall Return', f"{portfolio_data['overall_return']:.2f}%"],
        ['Number of Holdings', str(portfolio_data['num_holdings'])],
        ['Number of Sectors', str(len(portfolio_data['sectors']))]
    ]
    
    summary_table = Table(summary_data, colWidths=[180, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F7FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8)
    ]))
    
    content.append(summary_table)
    content.append(Spacer(1, 15))
    
    # Add pie charts if available
    if portfolio_data.get('sector_chart'):
        content.append(Paragraph("Sector Distribution", section_style))
        sector_chart_path = create_pie_chart_for_pdf(
            portfolio_data['sector_distribution'],
            "Sector Distribution"
        )
        if sector_chart_path:
            sector_img = Image(sector_chart_path, width=4*inch, height=3*inch)
            content.append(sector_img)
            content.append(Spacer(1, 10))
    
    if portfolio_data.get('market_cap_chart'):
        content.append(Paragraph("Market Cap Distribution", section_style))
        cap_chart_path = create_pie_chart_for_pdf(
            portfolio_data['market_cap_distribution'],
            "Market Cap Distribution"
        )
        if cap_chart_path:
            cap_img = Image(cap_chart_path, width=4*inch, height=3*inch)
            content.append(cap_img)
            content.append(Spacer(1, 10))
    
    # Top Holdings
    content.append(Paragraph("Top 10 Holdings", section_style))
    
    holdings_data = [['Stock', 'Sector', 'Value (₹)', 'Return %']]
    for holding in portfolio_data.get('top_holdings', [])[:10]:
        holdings_data.append([
            holding['name'][:20],
            holding['sector'][:15],
            f"₹{holding['value']:,.0f}",
            f"{holding['return_pct']:.1f}%"
        ])
    
    holdings_table = Table(holdings_data, colWidths=[90, 70, 80, 50])
    holdings_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4299E1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    content.append(holdings_table)
    content.append(Spacer(1, 15))
    
    # Performance Highlights
    content.append(Paragraph("Performance Highlights", section_style))
    
    perf_data = [['', 'Stock', 'Return %', 'Gain/Loss (₹)']]
    
    # Top gainers
    for gainer in portfolio_data.get('top_gainers', [])[:3]:
        perf_data.append([
            'Top Gainer',
            gainer['name'][:15],
            f"{gainer['return_pct']:.1f}%",
            f"₹{gainer['gain_loss']:,.0f}"
        ])
    
    # Top losers
    for loser in portfolio_data.get('top_losers', [])[:3]:
        perf_data.append([
            'Top Loser',
            loser['name'][:15],
            f"{loser['return_pct']:.1f}%",
            f"₹{loser['gain_loss']:,.0f}"
        ])
    
    perf_table = Table(perf_data, colWidths=[60, 80, 50, 80])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ED8936')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    content.append(perf_table)
    content.append(Spacer(1, 15))
    
    # Risk Metrics
    content.append(Paragraph("Risk Assessment", section_style))
    
    risk_data = [
        ['Metric', 'Value', 'Assessment'],
        ['Concentration (Top 5)', f"{portfolio_data['concentration_risk']:.1f}%", 
         'High' if portfolio_data['concentration_risk'] > 50 else 'Moderate' if portfolio_data['concentration_risk'] > 40 else 'Low'],
        ['Largest Sector', f"{portfolio_data['top_sector'][:15]} ({portfolio_data['top_sector_pct']:.1f}%)",
         'High' if portfolio_data['top_sector_pct'] > 40 else 'Moderate' if portfolio_data['top_sector_pct'] > 30 else 'Low']
    ]
    
    risk_table = Table(risk_data, colWidths=[100, 80, 70])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F56565')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    content.append(risk_table)
    
    # Footer
    content.append(Spacer(1, 20))
    content.append(Paragraph(
        "Generated by Portfolio Health Report Generator",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=6, textColor=colors.grey, alignment=1)
    ))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer