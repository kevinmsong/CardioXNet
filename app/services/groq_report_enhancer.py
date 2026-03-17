"""Groq AI-powered report enhancement using Llama 3.1 Instant."""

import logging
import os
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class GroqReportEnhancer:
    """
    Enhances CardioXNet analysis reports using Groq's Llama 3.1 Instant model.

    Generates:
    - Executive summary narrative
    - Pathway interpretation paragraphs
    - Therapeutic opportunity highlights
    - Scientific discussion sections
    """

    MODEL = "llama-3.1-8b-instant"

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Groq client from env variable."""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set — AI narrative generation disabled")
            return
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key)
            logger.info(f"GroqReportEnhancer initialized (model: {self.MODEL})")
        except ImportError:
            logger.warning("groq package not installed — install with: pip install groq")
        except Exception as e:
            logger.warning(f"Groq client init failed: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def _call(self, system_prompt: str, user_prompt: str, max_tokens: int = 800) -> Optional[str]:
        """Call Groq API with error handling."""
        if not self.client:
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}")
            return None

    def generate_executive_summary(self, report_data: Dict[str, Any]) -> str:
        """Generate a concise executive summary of the analysis."""
        seed_genes = report_data.get("seed_genes", [])
        top_pathways = report_data.get("top_pathways", [])[:5]
        top_genes = report_data.get("top_genes", [])[:5]
        disease_context = report_data.get("disease_context", "cardiovascular disease")

        pathway_names = [p.get("name", "") for p in top_pathways if p.get("name")]
        gene_names = [g.get("gene_symbol", g.get("symbol", "")) for g in top_genes]

        system = (
            "You are a cardiovascular disease research scientist writing a structured "
            "bioinformatics report. Be precise, scientific, and concise. "
            "Write in the third person. Do not use bullet points — write prose paragraphs."
        )

        user = f"""Write a 3-paragraph executive summary for a CardioXNet pathway analysis.

Input genes: {', '.join(seed_genes[:15])}
Disease context: {disease_context}
Top discovered pathways: {', '.join(pathway_names[:5])}
Key therapeutic targets: {', '.join(gene_names[:5])}

Paragraph 1: Describe the biological significance of the input gene set in cardiovascular disease.
Paragraph 2: Summarize the most important pathway discoveries and their mechanistic relevance.
Paragraph 3: Highlight the therapeutic opportunities and translational implications.

Write concise, scientific English. 3 paragraphs, ~80 words each."""

        result = self._call(system, user, max_tokens=700)
        if result:
            logger.info("Groq: executive summary generated")
        return result or self._fallback_executive_summary(seed_genes, pathway_names, disease_context)

    def _fallback_executive_summary(self, seed_genes: List[str], pathway_names: List[str], disease_context: str) -> str:
        genes_str = ", ".join(seed_genes[:8]) + (f" and {len(seed_genes) - 8} others" if len(seed_genes) > 8 else "")
        pathways_str = "; ".join(pathway_names[:3]) if pathway_names else "cardiac signaling pathways"
        return (
            f"This CardioXNet analysis examined {len(seed_genes)} cardiovascular-associated genes "
            f"({genes_str}) to identify disease-relevant molecular pathways in the context of {disease_context}. "
            f"Using the NETS pipeline, seed genes were expanded through STRING v11.5 protein-protein interaction "
            f"networks and subjected to multi-database pathway enrichment analysis.\n\n"
            f"The analysis identified {len(pathway_names)} statistically significant pathways after semantic "
            f"cardiac filtering and permutation-based validation. Key discoveries include: {pathways_str}. "
            f"These pathways were prioritized by Network Enrichment Score (NES) combining statistical significance, "
            f"gene set size normalization, and database quality weighting.\n\n"
            f"Druggability analysis identified pathway genes with existing FDA-approved therapeutic interventions "
            f"or active clinical development programs, representing immediate translational opportunities for "
            f"cardiovascular disease management."
        )

    def generate_pathway_interpretation(self, pathway: Dict[str, Any], rank: int) -> str:
        """Generate a detailed interpretation paragraph for a single pathway."""
        name = pathway.get("name", "Unknown Pathway")
        nes = pathway.get("nes_score", 0)
        pval = pathway.get("p_value", 1.0)
        genes = pathway.get("evidence_genes", [])[:8]
        database = pathway.get("database", "")
        cardiac_score = pathway.get("cardiac_disease_score", 0)

        system = (
            "You are a cardiovascular biology expert. Write a concise scientific interpretation "
            "of a pathway discovered in a cardiovascular disease gene network analysis. "
            "One paragraph, ~60 words, scientific tone, no bullet points."
        )

        user = f"""Interpret this pathway discovery for a cardiovascular disease report:

Rank: #{rank}
Pathway: {name}
Database: {database}
NES Score: {nes:.2f}
P-value: {pval:.2e}
Key genes: {', '.join(genes)}
Cardiac disease relevance score: {cardiac_score:.2f}

Write one concise scientific paragraph explaining the biological significance of this pathway in cardiovascular disease context."""

        result = self._call(system, user, max_tokens=200)
        return result or f"**{name}** (NES={nes:.2f}, p={pval:.2e}) was identified as a significant cardiovascular pathway involving {', '.join(genes[:4])}."

    def generate_therapeutic_discussion(self, top_genes: List[Dict], druggability_data: Dict) -> str:
        """Generate a therapeutic targets discussion section."""
        high_tier = [g for g in top_genes if g.get("druggability_tier") == "high"][:5]
        medium_tier = [g for g in top_genes if g.get("druggability_tier") == "medium"][:3]

        high_names = [g.get("gene_symbol", g.get("symbol", "")) for g in high_tier]
        medium_names = [g.get("gene_symbol", g.get("symbol", "")) for g in medium_tier]

        system = (
            "You are a cardiovascular pharmacology expert. Write a scientific discussion "
            "of therapeutic targets discovered in a pathway analysis. "
            "2 short paragraphs, ~70 words each, scientific tone."
        )

        user = f"""Write a therapeutic targets discussion for a CardioXNet report:

FDA-approved drug targets identified: {', '.join(high_names) or 'None'}
Clinical trial targets identified: {', '.join(medium_names) or 'None'}

Paragraph 1: Discuss the significance of the FDA-approved targets in cardiovascular therapy.
Paragraph 2: Discuss clinical trial opportunities and future therapeutic development."""

        result = self._call(system, user, max_tokens=350)
        if result:
            logger.info("Groq: therapeutic discussion generated")

        if not result:
            result = (
                f"The analysis identified {len(high_tier)} genes targeted by FDA-approved cardiovascular drugs"
                f"{(': ' + ', '.join(high_names)) if high_names else ''}, "
                f"providing immediate translational relevance. These represent validated drug targets "
                f"with established clinical efficacy in cardiovascular disease management.\n\n"
                f"Additionally, {len(medium_tier)} genes are currently in active clinical development"
                f"{(': ' + ', '.join(medium_names)) if medium_names else ''}, "
                f"representing emerging therapeutic opportunities that may yield new cardiovascular treatments."
            )
        return result

    def enhance_report_data(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add AI-generated sections to report_data dict.
        Safe to call even if Groq is unavailable (falls back to rule-based text).
        """
        enhanced = dict(report_data)

        # Executive summary
        enhanced["ai_executive_summary"] = self.generate_executive_summary(report_data)

        # Pathway interpretations (top 5 only to limit API calls)
        top_pathways = report_data.get("top_pathways", [])[:5]
        pathway_interpretations = []
        for i, pathway in enumerate(top_pathways, 1):
            interp = self.generate_pathway_interpretation(pathway, i)
            pathway_interpretations.append({"pathway": pathway, "interpretation": interp})
        enhanced["ai_pathway_interpretations"] = pathway_interpretations

        # Therapeutic discussion
        top_genes = report_data.get("top_genes", [])
        enhanced["ai_therapeutic_discussion"] = self.generate_therapeutic_discussion(top_genes, {})

        enhanced["ai_powered"] = self.is_available()
        return enhanced
