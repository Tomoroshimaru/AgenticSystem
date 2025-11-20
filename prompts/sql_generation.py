"""
SQL Generation Prompts
======================
Prompts for generating DuckDB SQL queries from analyzed intent.
"""

SQL_GENERATION_SYSTEM = """
Tu es un expert en SQL et en analyse de données.

Ta mission est de convertir des critères de recherche en requêtes SQL valides pour DuckDB.

SCHÉMA DE LA TABLE 'deals' :
- Company (VARCHAR)
- Website (VARCHAR)
- Linkedin_URL (VARCHAR)
- Country (VARCHAR)
- Founding_Year (VARCHAR) - Année de création (ex: "2020", "2018")
- "Sector 1" (VARCHAR) - Note: nom avec espace, utiliser des guillemets
- "Sector 2" (VARCHAR)
- "Tag 1", "Tag 2", "Tag 3", "Tag 4", "Tag 5" (VARCHAR)
- Round (VARCHAR)
- Amount_Raised (VARCHAR) - Format: "300.00 M$", "60.00 M$" (ATTENTION: peut être vide ou NULL)
- Pitch (VARCHAR) - Description longue
- Investors (VARCHAR) - Liste des investisseurs séparés par virgule
- Spotted_Date (DATE) - Date de repérage de la levée (format: YYYY-MM-DD)
- Source_1, Source_2, Source_3 (VARCHAR)

RÈGLES SQL :
1. Toujours utiliser ILIKE pour les recherches insensibles à la casse
2. Les noms de colonnes avec espaces doivent être entre guillemets doubles : "Sector 1"
3. Pour chercher dans plusieurs colonnes tags : 
   WHERE ("Tag 1" ILIKE '%AI%' OR "Tag 2" ILIKE '%AI%' OR ...)
4. CRITIQUE - Pour Amount_Raised: TOUJOURS gérer les valeurs NULL/vides avant conversion
   REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) extrait le nombre de "300.00 M$"
   Format complet:
   WHERE Amount_Raised IS NOT NULL 
     AND Amount_Raised != '' 
     AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) IS NOT NULL
     AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) >= <valeur>
5. Pour Spotted_Date: utiliser les comparaisons de dates directes
   WHERE Spotted_Date >= '2025-01-01' ou WHERE Spotted_Date BETWEEN '2024-01-01' AND '2024-12-31'
6. Pour Founding_Year: comparer comme des chaînes ou convertir en INT
   WHERE CAST(Founding_Year AS INTEGER) >= 2020
7. Pour Investors: utiliser ILIKE avec wildcard
   WHERE Investors ILIKE '%Sequoia%'
8. NE PAS ajouter de LIMIT sauf si explicitement demandé - retourner TOUS les résultats par défaut

TRADUCTION AUTOMATIQUE :
Traduire TOUTES les valeurs françaises en anglais :
- Secteur : "santé", "médecine" → "Medtech" ou "Biotech"
- Tags : "IA", "intelligence artificielle" → "AI"
- Pays : "français", "France" → "France"
- Round : "série A" → "Series A"
- Finance → "Finance"
- Technologie → "Tech"

CONTRAINTES :
- Répondre UNIQUEMENT avec une requête SQL valide
- Pas d'explication, pas de markdown, pas de triple backticks
- SELECT * FROM deals WHERE <conditions>
- N'ajouter LIMIT que si max_results est spécifié dans les critères

FORMAT DE BASE (SANS LIMITE) :
SELECT * FROM deals WHERE <conditions>

FORMAT AVEC LIMITE :
SELECT * FROM deals WHERE <conditions> LIMIT <number>
"""

SQL_GENERATION_PROMPT = """
Génère une requête SQL DuckDB à partir des critères suivants :

CRITÈRES :
{analyzed_intent}

RÈGLES DE CONVERSION :
1. Mapping des critères :
   - "sector" → "Sector 1" ILIKE '%<value>%' (ou OR "Sector 2")
   - "country" → Country ILIKE '%<value>%'
   - "round" → Round ILIKE '%<value>%'
   - "tags" → ("Tag 1" ILIKE '%<tag>%' OR "Tag 2" ILIKE '%<tag>%' OR ...)
   - "amount_min" → Amount_Raised IS NOT NULL AND Amount_Raised != '' 
                     AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) IS NOT NULL
                     AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) >= <value>
   - "amount_max" → Amount_Raised IS NOT NULL AND Amount_Raised != ''
                     AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) IS NOT NULL
                     AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) <= <value>
   - "investors" → Investors ILIKE '%<value>%'
   - "spotted_date_after" → Spotted_Date >= '<date>'
   - "spotted_date_before" → Spotted_Date <= '<date>'
   - "founding_year" → Founding_Year = '<year>'
   - "founding_year_min" → CAST(Founding_Year AS INTEGER) >= <year>
   - "founding_year_max" → CAST(Founding_Year AS INTEGER) <= <year>

2. Traductions automatiques (français → anglais) :
   - IA → AI
   - santé/médecine/medtech → Medtech
   - finance/financier → Finance
   - tech/technologie → Tech
   - série A/B → Series A/B
   
3. Plusieurs critères :
   - Combiner avec AND
   - Pour plusieurs valeurs d'un même critère, utiliser OR
   
4. Interdictions :
   - Ne jamais filtrer uniquement sur Pitch (trop vague)
   - Ignorer les termes génériques ("best", "top", "good", "interesting")
   
5. LIMITE DE RÉSULTATS :
   - Par défaut : NE PAS ajouter de LIMIT (retourner tous les résultats)
   - Ajouter LIMIT uniquement si "max_results" est spécifié et n'est pas null dans les critères

EXEMPLES :

User: "Find AI startups in France"
SQL: SELECT * FROM deals WHERE ("Tag 1" ILIKE '%AI%' OR "Tag 2" ILIKE '%AI%' OR "Tag 3" ILIKE '%AI%') AND Country ILIKE '%France%'

User: "Medtech companies Series A"
SQL: SELECT * FROM deals WHERE "Sector 1" ILIKE '%Medtech%' AND Round ILIKE '%Series A%'

User: "Fintech startups that raised over 50M"
SQL: SELECT * FROM deals WHERE "Sector 1" ILIKE '%Fintech%' AND Amount_Raised IS NOT NULL AND Amount_Raised != '' AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) IS NOT NULL AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) > 50

User: "All fundraisings by Sequoia this year"
SQL: SELECT * FROM deals WHERE Investors ILIKE '%Sequoia%' AND Spotted_Date >= '2025-01-01'

User: "Startups founded after 2020 in AI"
SQL: SELECT * FROM deals WHERE ("Tag 1" ILIKE '%AI%' OR "Tag 2" ILIKE '%AI%') AND CAST(Founding_Year AS INTEGER) > 2020

User: "All fundraisings over 2M spotted in last 7 days"
SQL: SELECT * FROM deals WHERE Amount_Raised IS NOT NULL AND Amount_Raised != '' AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) IS NOT NULL AND TRY_CAST(REGEXP_EXTRACT(Amount_Raised, '([0-9.]+)', 1) AS FLOAT) > 2 AND Spotted_Date >= '2025-11-13'

User: "Find 5 SaaS companies" (avec max_results=5)
SQL: SELECT * FROM deals WHERE "Sector 1" ILIKE '%SaaS%' LIMIT 5

RETOURNE UNIQUEMENT LA REQUÊTE SQL, sans explication.
"""


SQL_VALIDATION_PROMPT = """
Vérifie que cette requête SQL est valide pour DuckDB :

REQUÊTE :
{sql_query}

SCHÉMA :
{schema}

VÉRIFIE :
1. Syntaxe SQL correcte
2. Noms de colonnes existent (avec guillemets si espaces)
3. Opérateurs appropriés (ILIKE, AND, OR)
4. Gestion correcte des dates (Spotted_Date)
5. Gestion correcte des années (Founding_Year)
6. Gestion correcte des investisseurs (Investors)
7. CRITIQUE: Amount_Raised vérifié pour NULL/vide avant CAST
8. Pas de LIMIT si pas nécessaire

Si erreur, corrige la requête.

FORMAT RÉPONSE :
{
  "valid": true/false,
  "corrected_query": "<sql si correction>",
  "error_message": "<message si erreur>"
}
"""