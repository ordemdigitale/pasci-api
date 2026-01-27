# PASCI API

API Rest pour le projet PASCI, développé avec FastAPI.

## 📋 Prérequis

Avant de commencer, assurez-vous d'avoir installé les outils suivants sur votre machine :

- [Python](https://nodejs.org/) (version 12 recommandée)
- [uv: gestionnaire de package Python](https://docs.astral.sh/uv/)

## 🚀 Installation

1. **Cloner le projet**

   ```bash
   git clone https://github.com/ordemdigitale/pasci-api.git
   cd pasci-api
   ```

2. **Installer les dépendances**

   ```bash
   uv sync
   ```

3. **Activer l'environnement virtuel**

   ```bash
   windows
   source .venv/Scripts/activate
   ```

   ```bash
   linux
   source .venv/bin/activate
   ```

## 📱 Lancer l'application

Pour démarrer le serveur de développement :

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
