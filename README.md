# 🤖 Investment Agent

Un système agent intelligent pour analyser et enrichir des levées de fonds à partir d'une base Notion.

## 🎯 Fonctionnalités

- 🔍 **Analyse d'intention** : Comprend vos requêtes en langage naturel
- 🗄️ **Recherche Notion** : Interroge votre base de données de levées
- 👤 **Human-in-the-loop** : Vous choisissez quelles levées enrichir
- 🌐 **Enrichissement web** : Trouve des entreprises similaires via recherche web
- 📄 **Génération PDF** : Crée un rapport professionnel
- ☁️ **Upload Drive** : Partage automatiquement sur Google Drive

## 🏗️ Architecture

Le système utilise **LangGraph** pour orchestrer un workflow en 7 étapes :
```
User Query → Intent Analysis → Query Generation → Notion Fetch 
→ Human Review → Web Enrichment → PDF Generation → Drive Upload
```

## 📋 Prérequis

- Python 3.10+
- Compte OpenAI (GPT-4)
- Base de données Notion
- API Serper (recherche web)
- Google Drive API (optionnel)

## 🚀 Installation

### 1. Cloner et setup
```bash
cd AgenticSystem
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### 2. Configuration

Créer un fichier `.env` :
```bash
cp .env.example .env
```

Remplir avec vos clés API :
```env
OPENAI_API_KEY=sk-...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
SERPER_API_KEY=...
GOOGLE_CREDENTIALS_PATH=./credentials.json  # optionnel
```

### 3. Structure Notion requise

Votre base Notion doit avoir ces colonnes :
- `company` (texte)
- `website` (texte)
- `country` (texte)
- `Sector` (texte)
- `Tag 1`, `Tag 2`, `Tag 3` (texte)
- `Amount raised` (texte)
- `Round` (texte)
- `Pitch` (texte)

## 💻 Utilisation

### Mode interactif
```bash
python main.py
```

Puis suivez les instructions :
1. Entrez votre requête (ex: "Trouve des levées SaaS en Serie A")
2. Sélectionnez les deals à enrichir
3. Récupérez le rapport PDF

### Mode ligne de commande
```bash
python main.py "Trouve des startups fintech en seed en France"
```

### Exemples de requêtes
```
✓ "Trouve des levées SaaS en Serie A en France"
✓ "Cherche des startups fintech entre 2M et 10M"
✓ "Levées Serie B en Europe secteur IA"
✓ "Startups insurtech en seed"
```

## 🧪 Tests
```bash
python test_workflow.py
```

## 📂 Structure du projet
```
AgenticSystem/
├── state.py              # Schéma du State (Pydantic)
├── config.py             # Configuration centralisée
├── main.py               # Orchestration LangGraph
├── prompts/              # Templates de prompts
├── tools/                # Wrappers API (Notion, Serper, Drive)
├── nodes/                # Logique des 7 nodes
└── utils/                # Utilitaires
```

## 🔧 Configuration avancée

### Ajuster les poids de similarité

Dans `config.py` :
```python
class SimilarityWeights:
    SECTOR_WEIGHT = 0.30   # Poids du secteur
    ROUND_WEIGHT = 0.25    # Poids du round
    TAGS_WEIGHT = 0.25     # Poids des tags
    PITCH_WEIGHT = 0.20    # Poids de la description
```

### Modifier les limites
```python
class WorkflowConfig:
    MAX_NOTION_RESULTS = 10              # Max résultats Notion
    MIN_SIMILARITY_SCORE = 0.6           # Seuil de similarité
    MAX_SIMILAR_COMPANIES_PER_DEAL = 5   # Max cibles par deal
```

## 🐛 Troubleshooting

### Erreur "Module not found"
```bash
pip install -r requirements.txt
```

### Erreur API Notion

- Vérifier que l'intégration Notion a accès à la base
- Vérifier le `NOTION_DATABASE_ID` dans `.env`

### Erreur Google Drive

- Vérifier que `credentials.json` existe
- Activer Google Drive API dans Google Cloud Console

## 📝 Logs

Les logs sont dans `logs/investment_agent.log`
```bash
tail -f logs/investment_agent.log
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amazing`)
3. Commit (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Ouvrir une Pull Request

## 📄 Licence

MIT

## 👤 Auteur

NIGOTO

---

**Note** : Ce projet nécessite des clés API payantes (OpenAI, Serper). Consultez la tarification avant utilisation.