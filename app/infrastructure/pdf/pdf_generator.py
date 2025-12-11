import logging
import os
import re
import asyncio
from openai import AsyncOpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.core.setup_config import settings

logger = logging.getLogger(__name__)

class StudyGuideGenerator:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.styles = self._setup_styles()

    def _setup_styles(self):
        """Configura los estilos de ReportLab (síncrono, es rápido)."""
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='MainHeader', parent=styles['Heading1'], fontSize=18, spaceBefore=20))
        styles.add(ParagraphStyle(name='SubHeader', parent=styles['Heading2'], fontSize=14, spaceBefore=12))
        styles.add(ParagraphStyle(name='ThirdHeader', parent=styles['Heading3'], fontSize=12, spaceBefore=10))
        styles.add(ParagraphStyle(name='BulletText', parent=styles['BodyText'], leftIndent=15))
        return styles

    async def generate_content(self, summary_text: str) -> str:
        """Usa GPT-4o para estructurar el contenido del PDF."""
        prompt = f"""
        Transforma el siguiente resumen en una Guía de Estudio estructurada para un PDF.
        Usa formato Markdown simple (# Titulo, ## Subtitulo, - Viñeta).
        Enfócate en conceptos clave, ejemplos y aplicabilidad.
        Idioma: Español.
        
        Resumen:
        {summary_text[:10000]}
        """
        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generando contenido PDF con AI: {e}")
            raise e

    def _create_pdf_sync(self, content: str, output_path: str):
        """
        Lógica de ReportLab (Síncrona - CPU Bound).
        Parsea el markdown básico y genera el PDF.
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            elements = []

            for line in content.split('\n'):
                line = line.strip()
                if not line: continue
                
                # Mapeo simple de Markdown a Estilos
                if line.startswith('# '):
                    elements.append(Paragraph(line[2:], self.styles['MainHeader']))
                elif line.startswith('## '):
                    elements.append(Paragraph(line[3:], self.styles['SubHeader']))
                elif line.startswith('### '):
                    elements.append(Paragraph(line[4:], self.styles['ThirdHeader']))
                elif line.startswith('- '):
                    elements.append(Paragraph(line[2:], self.styles['BulletText'], bulletText='•'))
                else:
                    # Negritas simples **texto** -> <b>texto</b>
                    line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                    elements.append(Paragraph(line, self.styles['Normal']))
                
                elements.append(Spacer(1, 6))

            doc.build(elements)
            logger.info(f"PDF generado localmente: {output_path}")
            
        except Exception as e:
            logger.error(f"Error construyendo PDF con ReportLab: {e}")
            raise e

    async def create_study_guide(self, summary_text: str, output_path: str):
        """Orquestador asíncrono de la generación."""
        # 1. Generar contenido (IO Bound - Async)
        content = await self.generate_content(summary_text)
        
        # 2. Crear PDF (CPU Bound - Ejecutar en thread aparte)
        await asyncio.to_thread(self._create_pdf_sync, content, output_path)
        
        return output_path