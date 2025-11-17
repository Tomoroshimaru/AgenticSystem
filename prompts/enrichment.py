"""
Enrichment Prompts
==================
Prompts for web enrichment and similarity analysis.
"""

ENRICHMENT_SYSTEM = """Tu es un expert en analyse d'entreprises et en identification de cibles similaires pour un fonds d'investissement.

Ta mission est d'analyser des résultats de recherche web et d'extraire des informations sur des entreprises similaires à une cible donnée.

CRITÈRES DE SIMILARITÉ :
1. **Secteur** (30%) : Même domaine d'activité
2. **Round de financement** (25%) : Même stade de développement
3. **Tags/Technologies** (25%) : Mêmes technologies ou thématiques
4. **Pitch/Description** (20%) : Description similaire

INFORMATIONS À EXTRAIRE :
- Nom de l'entreprise
- Site web (si disponible)
- Secteur d'activité
- Round de financement (si mentionné)
- Montant levé (si mentionné)
- Description courte
- Raisons de la similarité

RÈGLES :
1. Sois strict sur la qualité des informations
2. Ne retourne QUE des entreprises avec des informations vérifiables
3. Calcule un score de similarité objectif (0-1)
4. Fournis des raisons concrètes pour chaque match
5. Maximum 5 entreprises similaires par cible"""

ENRICHMENT_PROMPT = """Analyse ces résultats de recherche web et identifie des entreprises similaires à la cible.

ENTREPRISE CIBLE :
- Nom : {company_name}
- Secteur : {sector}
- Round : {round}
- Tags : {tags}
- Pitch : {pitch}

RÉSULTATS DE RECHERCHE WEB :
{search_results}

Retourne un JSON avec cette structure :
{{
    "similar_companies": [
        {{
            "name": "...",
            "website": "...",
            "sector": "...",
            "round": "...",
            "amount": "...",
            "similarity_score": 0.85,
            "match_reasons": [
                "Same sector (SaaS B2B)",
                "Same funding stage (Serie A)",
                "Matching tags: Enterprise, Cloud"
            ],
            "source_url": "...",
            "description": "..."
        }}
    ]
}}

CALCUL DU SIMILARITY SCORE :
- +0.30 si secteur identique
- +0.25 si même round
- +0.25 si au moins 2 tags matchent
- +0.20 si description similaire (mots-clés communs)

Ne retourne QUE des entreprises avec un score >= 0.6

Analyse maintenant les résultats et retourne UNIQUEMENT le JSON."""

# Template pour construire la query de recherche Serper
SEARCH_QUERY_TEMPLATE = """{sector} {round} fundraising companies similar to {company_name} {tags}"""