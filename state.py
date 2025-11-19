"""
State Management for Investment Agent
======================================
Defines the shared state schema using Pydantic models for validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================================
# PYDANTIC MODELS - Data Structures
# ============================================================================

class Deal(BaseModel):
    """Structure d'une levée de fonds (source: CSV via DuckDB)"""
    
    company: str = Field(..., description="Nom de l'entreprise")
    website: Optional[str] = Field(None, description="URL du site web")
    linkedin_url: Optional[str] = Field(None, description="URL LinkedIn")
    country: Optional[str] = Field(None, description="Pays")
    founding_year: Optional[str] = Field(None, description="Année de création")
    sector: Optional[str] = Field(None, description="Secteur d'activité principal")
    sector_2: Optional[str] = Field(None, description="Secteur secondaire")
    tags: List[str] = Field(default_factory=list, description="Tags/mots-clés")
    amount_raised: Optional[str] = Field(None, description="Montant levé (format texte)")
    round: Optional[str] = Field(None, description="Type de round (Seed, Serie A, etc.)")
    pitch: Optional[str] = Field(None, description="Description de l'entreprise")
    investors: Optional[str] = Field(None, description="Investisseurs")
    spotted_date: Optional[str] = Field(None, description="Date de repérage")
    source_urls: List[str] = Field(default_factory=list, description="URLs sources")
    
    class Config:
        json_schema_extra = {
            "example": {
                "company": "Acme Corp",
                "website": "https://acme.com",
                "linkedin_url": "https://linkedin.com/company/acme",
                "country": "France",
                "founding_year": "2020",
                "sector": "SaaS B2B",
                "sector_2": "Cloud",
                "tags": ["Enterprise", "AI", "Security"],
                "amount_raised": "5.00 M$",
                "round": "Series A",
                "pitch": "Cloud security platform for enterprises",
                "investors": "Sequoia, Accel",
                "spotted_date": "2025-01-15",
                "source_urls": ["https://techcrunch.com/..."]
            }
        }


class AnalyzedIntent(BaseModel):
    """Intent utilisateur structuré après analyse"""
    
    query_type: str = Field(
        default="fundraising_search",
        description="Type de recherche"
    )
    criteria: Dict[str, Any] = Field(
        default_factory=dict,
        description="Critères de filtrage extraits"
    )
    max_results: int = Field(
        default=10,
        le=20,
        ge=1,
        description="Nombre maximum de résultats"
    )
    raw_query: str = Field(default="", description="Requête originale")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_type": "fundraising_search",
                "criteria": {
                    "sector": "SaaS",
                    "round": "Serie A",
                    "country": "France",
                    "tags": ["Enterprise", "B2B"],
                    "keywords": ["cloud", "security"]
                },
                "max_results": 10,
                "raw_query": "Trouve moi des levées SaaS en Serie A en France"
            }
        }


class SimilarCompany(BaseModel):
    """Une entreprise similaire trouvée via recherche web"""
    
    name: str = Field(..., description="Nom de l'entreprise")
    website: Optional[str] = Field(None, description="URL du site")
    sector: Optional[str] = Field(None, description="Secteur")
    round: Optional[str] = Field(None, description="Type de round")
    amount: Optional[str] = Field(None, description="Montant levé")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score de similarité (0-1)"
    )
    match_reasons: List[str] = Field(
        default_factory=list,
        description="Raisons du matching"
    )
    source_url: str = Field(..., description="URL source de l'information")
    description: Optional[str] = Field(None, description="Description de l'entreprise")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "CompetitorX",
                "website": "https://competitorx.com",
                "sector": "SaaS B2B",
                "round": "Serie A",
                "amount": "7M€",
                "similarity_score": 0.85,
                "match_reasons": [
                    "Same sector (SaaS)",
                    "Same round (Serie A)",
                    "2 matching tags"
                ],
                "source_url": "https://techcrunch.com/...",
                "description": "Enterprise cloud security platform"
            }
        }


class EnrichedDeal(BaseModel):
    """Une levée enrichie avec des cibles similaires"""
    
    original_deal: Deal = Field(..., description="Deal original")
    similar_companies: List[SimilarCompany] = Field(
        default_factory=list,
        description="Liste des entreprises similaires trouvées"
    )
    enrichment_date: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Date de l'enrichissement"
    )
    enrichment_success: bool = Field(
        default=True,
        description="Succès de l'enrichissement"
    )


class ErrorLog(BaseModel):
    """Log d'erreur structuré"""
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp de l'erreur"
    )
    node: str = Field(..., description="Node où l'erreur s'est produite")
    error_type: str = Field(..., description="Type d'erreur")
    message: str = Field(..., description="Message d'erreur")
    retry_possible: bool = Field(default=True, description="Retry possible")
    details: Optional[Dict[str, Any]] = Field(None, description="Détails additionnels")


# ============================================================================
# MAIN STATE - Graph State Schema
# ============================================================================

class InvestmentState(BaseModel):
    """
    État partagé du workflow d'investissement.
    Cet état circule entre tous les nodes du graph LangGraph.
    """
    
    # === CONVERSATION ===
    messages: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Historique de la conversation (role + content)"
    )
    
    # === ÉTAPE 1: INTENT ANALYSIS ===
    user_query: str = Field(
        default="",
        description="Requête utilisateur originale"
    )
    analyzed_intent: Optional[AnalyzedIntent] = Field(
        None,
        description="Intent structuré après analyse"
    )
    
    # === ÉTAPE 2: QUERY GENERATION ===
    generated_query: str = Field(
        default="",
        description="Requête SQL générée"
    )
    query_valid: bool = Field(
        default=False,
        description="Validation de la requête générée"
    )
    query_errors: List[str] = Field(
        default_factory=list,
        description="Erreurs de validation de la requête"
    )
    
    # === ÉTAPE 3: DATA FETCH ===
    deals: List[Deal] = Field(
        default_factory=list,
        description="Résultats bruts (deals from CSV)"
    )
    results_count: int = Field(
        default=0,
        description="Nombre de résultats"
    )
    
    # === ÉTAPE 4: HUMAN REVIEW (HITL) ===
    selected_deal_ids: List[int] = Field(
        default_factory=list,
        description="Indices des deals sélectionnés par l'utilisateur (0-based)"
    )
    user_feedback: Optional[str] = Field(
        None,
        description="Feedback optionnel de l'utilisateur"
    )
    
    # === ÉTAPE 5: WEB ENRICHMENT ===
    enriched_deals: List[EnrichedDeal] = Field(
        default_factory=list,
        description="Deals enrichis avec cibles similaires"
    )
    enrichment_criteria: Dict[str, Any] = Field(
        default_factory=lambda: {
            "match_fields": ["sector", "tags", "round"],
            "min_similarity": 0.6,
            "max_similar_per_deal": 5
        },
        description="Critères d'enrichissement"
    )
    total_similar_companies: int = Field(
        default=0,
        description="Nombre total de cibles similaires trouvées"
    )
    
    # === ÉTAPE 6: PDF GENERATION ===
    pdf_generated: bool = Field(
        default=False,
        description="Statut de génération du PDF"
    )
    pdf_local_path: Optional[str] = Field(
        None,
        description="Chemin local du PDF généré"
    )
    
    # === ÉTAPE 7: GOOGLE DRIVE ===
    drive_upload_success: bool = Field(
        default=False,
        description="Succès de l'upload Drive"
    )
    drive_file_url: Optional[str] = Field(
        None,
        description="URL publique du fichier sur Drive"
    )
    drive_file_id: Optional[str] = Field(
        None,
        description="ID du fichier sur Drive"
    )
    
    # === META / CONTRÔLE ===
    current_step: str = Field(
        default="start",
        description="Étape actuelle du workflow"
    )
    errors: List[ErrorLog] = Field(
        default_factory=list,
        description="Liste des erreurs rencontrées"
    )
    retry_count: int = Field(
        default=0,
        description="Compteur de retries"
    )
    workflow_complete: bool = Field(
        default=False,
        description="Workflow complété avec succès"
    )
    
    class Config:
        arbitrary_types_allowed = True


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_message(state: InvestmentState, role: str, content: str) -> InvestmentState:
    """Ajoute un message à l'historique de conversation"""
    state.messages.append({"role": role, "content": content})
    return state


def add_error(
    state: InvestmentState,
    node: str,
    error_type: str,
    message: str,
    retry_possible: bool = True,
    details: Optional[Dict[str, Any]] = None
) -> InvestmentState:
    """Ajoute une erreur au log d'erreurs"""
    error = ErrorLog(
        node=node,
        error_type=error_type,
        message=message,
        retry_possible=retry_possible,
        details=details
    )
    state.errors.append(error)
    return state


def get_selected_deals(state: InvestmentState) -> List[Deal]:
    """Récupère les deals sélectionnés par l'utilisateur"""
    return [
        state.deals[i]
        for i in state.selected_deal_ids
        if i < len(state.deals)
    ]


def calculate_total_similar_companies(state: InvestmentState) -> int:
    """Calcule le nombre total de cibles similaires trouvées"""
    return sum(len(ed.similar_companies) for ed in state.enriched_deals)
