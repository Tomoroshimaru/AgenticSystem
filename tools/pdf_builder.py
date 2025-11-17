"""
PDF Report Builder
==================
Generates PDF reports for investment deals and similar companies.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image
)
from loguru import logger

from state import EnrichedDeal, NotionDeal, SimilarCompany


class PDFReportBuilder:
    """Builder pour générer des rapports PDF d'investissement"""
    
    def __init__(self, output_dir: str = "./output"):
        """
        Initialize PDF builder
        
        Args:
            output_dir: Directory to save PDF files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        logger.info("PDF Builder initialized")
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # Deal header style
        self.styles.add(ParagraphStyle(
            name='DealHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#0066cc'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Body style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=6,
            alignment=TA_LEFT
        ))
    
    def generate_report(
        self,
        enriched_deals: List[EnrichedDeal],
        user_query: str,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Generate a complete investment report PDF
        
        Args:
            enriched_deals: List of enriched deals with similar companies
            user_query: Original user query
            output_filename: Custom filename (auto-generated if None)
            
        Returns:
            Path to generated PDF file
        """
        try:
            # Generate filename
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"investment_report_{timestamp}.pdf"
            
            output_path = self.output_dir / output_filename
            
            logger.info(f"Generating PDF report: {output_path}")
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Build content
            story = []
            
            # Add cover page
            story.extend(self._build_cover_page(user_query, enriched_deals))
            story.append(PageBreak())
            
            # Add executive summary
            story.extend(self._build_executive_summary(enriched_deals))
            story.append(PageBreak())
            
            # Add deal details
            for i, enriched_deal in enumerate(enriched_deals):
                story.extend(self._build_deal_section(enriched_deal, i + 1))
                if i < len(enriched_deals) - 1:
                    story.append(PageBreak())
            
            # Add footer page
            story.append(PageBreak())
            story.extend(self._build_footer_page())
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"✅ PDF report generated: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
    
    def _build_cover_page(
        self,
        user_query: str,
        enriched_deals: List[EnrichedDeal]
    ) -> List:
        """Build the cover page"""
        content = []
        
        # Title
        content.append(Spacer(1, 3*cm))
        content.append(Paragraph(
            "Investment Deal Report",
            self.styles['CustomTitle']
        ))
        
        content.append(Spacer(1, 1*cm))
        
        # Query info
        content.append(Paragraph(
            f"<b>Search Query:</b> {user_query}",
            self.styles['CustomBody']
        ))
        
        content.append(Spacer(1, 0.5*cm))
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        content.append(Paragraph(
            f"<b>Generated:</b> {date_str}",
            self.styles['CustomBody']
        ))
        
        content.append(Spacer(1, 2*cm))
        
        # Quick stats
        total_deals = len(enriched_deals)
        total_similar = sum(len(ed.similar_companies) for ed in enriched_deals)
        
        stats_data = [
            ["Metric", "Value"],
            ["Deals Analyzed", str(total_deals)],
            ["Similar Companies Found", str(total_similar)],
            ["Average per Deal", f"{total_similar / total_deals:.1f}" if total_deals > 0 else "0"]
        ]
        
        stats_table = Table(stats_data, colWidths=[10*cm, 5*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f0f0')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(stats_table)
        
        return content
    
    def _build_executive_summary(self, enriched_deals: List[EnrichedDeal]) -> List:
        """Build executive summary page"""
        content = []
        
        content.append(Paragraph("Executive Summary", self.styles['CustomTitle']))
        content.append(Spacer(1, 0.5*cm))
        
        # Summary table
        summary_data = [["Company", "Sector", "Round", "Amount", "Similar Found"]]
        
        for ed in enriched_deals:
            deal = ed.original_deal
            summary_data.append([
                deal.company,
                deal.sector or "N/A",
                deal.round or "N/A",
                deal.amount_raised or "N/A",
                str(len(ed.similar_companies))
            ])
        
        summary_table = Table(summary_data, colWidths=[4*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        content.append(summary_table)
        
        return content
    
    def _build_deal_section(self, enriched_deal: EnrichedDeal, deal_number: int) -> List:
        """Build a section for one deal with similar companies"""
        content = []
        
        deal = enriched_deal.original_deal
        
        # Deal header
        content.append(Paragraph(
            f"Deal #{deal_number}: {deal.company}",
            self.styles['DealHeader']
        ))
        
        # Deal details table
        deal_data = [
            ["Company", deal.company],
            ["Sector", deal.sector or "N/A"],
            ["Round", deal.round or "N/A"],
            ["Amount Raised", deal.amount_raised or "N/A"],
            ["Country", deal.country or "N/A"],
            ["Website", deal.website or "N/A"],
        ]
        
        if deal.tag_1 or deal.tag_2 or deal.tag_3:
            tags = ", ".join(filter(None, [deal.tag_1, deal.tag_2, deal.tag_3]))
            deal_data.append(["Tags", tags])
        
        deal_table = Table(deal_data, colWidths=[5*cm, 10*cm])
        deal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e6e6e6')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        content.append(deal_table)
        content.append(Spacer(1, 0.3*cm))
        
        # Pitch
        if deal.pitch:
            content.append(Paragraph("<b>Description:</b>", self.styles['CustomBody']))
            content.append(Paragraph(deal.pitch, self.styles['CustomBody']))
            content.append(Spacer(1, 0.5*cm))
        
        # Similar companies
        content.append(Paragraph(
            f"Similar Companies ({len(enriched_deal.similar_companies)})",
            self.styles['CustomSubtitle']
        ))
        
        if enriched_deal.similar_companies:
            for i, similar in enumerate(enriched_deal.similar_companies):
                content.extend(self._build_similar_company(similar, i + 1))
        else:
            content.append(Paragraph(
                "No similar companies found.",
                self.styles['CustomBody']
            ))
        
        return content
    
    def _build_similar_company(self, similar: SimilarCompany, number: int) -> List:
        """Build section for one similar company"""
        content = []
        
        content.append(Spacer(1, 0.3*cm))
        
        # Company header with similarity score
        header_text = f"{number}. {similar.name} (Similarity: {similar.similarity_score:.0%})"
        content.append(Paragraph(header_text, self.styles['Heading4']))
        
        # Company details
        details = []
        if similar.sector:
            details.append(f"<b>Sector:</b> {similar.sector}")
        if similar.round:
            details.append(f"<b>Round:</b> {similar.round}")
        if similar.amount:
            details.append(f"<b>Amount:</b> {similar.amount}")
        if similar.website:
            details.append(f"<b>Website:</b> {similar.website}")
        
        if details:
            content.append(Paragraph(" | ".join(details), self.styles['CustomBody']))
        
        # Description
        if similar.description:
            content.append(Paragraph(similar.description, self.styles['CustomBody']))
        
        # Match reasons
        if similar.match_reasons:
            reasons_text = "<b>Match Reasons:</b> " + ", ".join(similar.match_reasons)
            content.append(Paragraph(reasons_text, self.styles['CustomBody']))
        
        # Source
        content.append(Paragraph(
            f"<i>Source: {similar.source_url}</i>",
            self.styles['CustomBody']
        ))
        
        return content
    
    def _build_footer_page(self) -> List:
        """Build footer/methodology page"""
        content = []
        
        content.append(Paragraph("Methodology", self.styles['CustomTitle']))
        content.append(Spacer(1, 0.5*cm))
        
        methodology_text = """
        <b>Similarity Scoring:</b><br/>
        Companies are scored based on multiple criteria:<br/>
        • Sector match: 30%<br/>
        • Funding round match: 25%<br/>
        • Tags/technology match: 25%<br/>
        • Description similarity: 20%<br/>
        <br/>
        Only companies with a similarity score ≥ 60% are included in this report.
        <br/><br/>
        <b>Data Sources:</b><br/>
        • Internal Notion database for original deals<br/>
        • Web search (Serper API) for similar companies<br/>
        <br/>
        <b>Generated by:</b> Investment Agent System<br/>
        <b>Date:</b> {date}
        """.format(date=datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        content.append(Paragraph(methodology_text, self.styles['CustomBody']))
        
        return content


# Utility function for testing
def test_pdf_generation():
    """Test PDF generation with sample data"""
    try:
        from state import NotionDeal, SimilarCompany, EnrichedDeal
        
        # Sample data
        deal = NotionDeal(
            id="test123",
            company="Test Corp",
            sector="SaaS",
            round="Serie A",
            amount_raised="5M€",
            country="France",
            pitch="A great company"
        )
        
        similar = SimilarCompany(
            name="Similar Corp",
            sector="SaaS",
            round="Serie A",
            amount="7M€",
            similarity_score=0.85,
            match_reasons=["Same sector", "Same round"],
            source_url="https://example.com"
        )
        
        enriched = EnrichedDeal(
            original_deal=deal,
            similar_companies=[similar]
        )
        
        builder = PDFReportBuilder()
        pdf_path = builder.generate_report([enriched], "Test query")
        
        logger.info(f"✅ Test PDF generated: {pdf_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ PDF generation test failed: {e}")
        return False
