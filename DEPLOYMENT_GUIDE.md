# Guide de déploiement PASCI sur Plesk

Ce guide vous accompagne dans le déploiement de l'application PASCI (Backend API FastAPI + Frontend Next.js) sur un serveur Plesk.

## Table des matières

1. [Prérequis](#prérequis)
2. [Partie 1 : Déploiement du Backend (API FastAPI)](#partie-1--déploiement-du-backend-api-fastapi)
3. [Partie 2 : Déploiement du Frontend (Next.js)](#partie-2--déploiement-du-frontend-nextjs)
4. [Configuration de la base de données](#configuration-de-la-base-de-données)
5. [Configuration SSL](#configuration-ssl)
6. [Maintenance et mises à jour](#maintenance-et-mises-à-jour)
7. [Dépannage](#dépannage)

---

## Prérequis

### Sur votre serveur Plesk

- Plesk Obsidian (version 18.0 ou supérieure recommandée)
- Python 3.13 ou supérieur
- PostgreSQL 14 ou supérieur
- Node.js 18 ou supérieur (pour Next.js)
- Accès SSH au serveur
- Un nom de domaine configuré (ex: `yourdomain.com`)
- Sous-domaine pour l'API (ex: `api.yourdomain.com`)

### Extensions Plesk recommandées

- Python Selector (pour gérer les versions Python)
- Node.js Manager (pour gérer Node.js)
- Git (pour déploiement via Git)

---

## Partie 1 : Déploiement du Backend (API FastAPI)

### Étape 1.1 : Créer un sous-domaine pour l'API

1. Connectez-vous à Plesk
2. Allez dans **Domaines** ’ Cliquez sur votre domaine
3. Cliquez sur **Sous-domaines**
4. Créez un nouveau sous-domaine : `api.yourdomain.com`
5. Définissez le document root : `/httpdocs/api` (ou selon votre préférence)

### Étape 1.2 : Créer la base de données PostgreSQL

1. Dans Plesk, allez dans **Bases de données**
2. Cliquez sur **Ajouter une base de données**
3. Sélectionnez **PostgreSQL**
4. Créez une base de données :
   - Nom : `pascidb`
   - Utilisateur : créez un utilisateur avec un mot de passe sécurisé
   - Notez les informations de connexion

### Étape 1.3 : Télécharger le code via SSH ou FTP

#### Option A : Via SSH (recommandé)

```bash
# Connectez-vous via SSH
ssh user@yourdomain.com

# Naviguez vers le répertoire du sous-domaine
cd /var/www/vhosts/yourdomain.com/api.yourdomain.com

# Clonez votre repository (si vous utilisez Git)
git clone https://github.com/votre-utilisateur/pasci-api.git .

# OU téléchargez vos fichiers via FTP/SCP
```

#### Option B : Via FTP

1. Connectez-vous via FTP
2. Naviguez vers `/httpdocs/api/`
3. Téléchargez tous les fichiers du dossier `pasci-api`

### Étape 1.4 : Configurer Python et l'environnement virtuel

```bash
# Connectez-vous via SSH
cd /var/www/vhosts/yourdomain.com/api.yourdomain.com

# Créez un environnement virtuel
python3.13 -m venv venv

# Activez l'environnement virtuel
source venv/bin/activate

# Installez les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

### Étape 1.5 : Configurer les variables d'environnement

```bash
# Copiez le fichier .env.example
cp .env.example .env

# Éditez le fichier .env avec vos valeurs
nano .env
```

Configurez les variables suivantes :

```env
SECRET_KEY=votre-clé-secrète-générée
ENVIRONMENT=production
DEBUG=False

DATABASE_URL=postgresql://db_user:db_password@localhost:5432/pascidb
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pascidb
DB_USER=votre_utilisateur_db
DB_PASSWORD=votre_mot_de_passe_db

ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
ALLOWED_HOSTS=api.yourdomain.com

FIRST_SUPERUSER_EMAIL=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=votre-mot-de-passe-admin
FIRST_SUPERUSER_USERNAME=admin
```

Pour générer une clé secrète sécurisée :

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Étape 1.6 : Initialiser la base de données

```bash
# Activez l'environnement virtuel si ce n'est pas déjà fait
source venv/bin/activate

# Exécutez les migrations Alembic
alembic upgrade head

# Vérifiez que la base de données est correctement configurée
python3 -c "from app.database.session import engine; print('Database connection successful!')"
```

### Étape 1.7 : Configurer Passenger (Plesk)

1. Dans Plesk, allez dans le sous-domaine `api.yourdomain.com`
2. Cliquez sur **Python**
3. Configurez :
   - **Version Python** : 3.13 (ou la version installée)
   - **Application root** : `/httpdocs/api`
   - **Application URL** : `/`
   - **Application startup file** : `passenger_wsgi.py`
   - **Application Entry Point** : `application`

4. Dans **Environment Variables**, ajoutez :
   ```
   PYTHONPATH=/var/www/vhosts/yourdomain.com/api.yourdomain.com
   ```

5. Cliquez sur **Redémarrer l'application**

### Étape 1.8 : Alternative avec Gunicorn (si Passenger ne fonctionne pas)

Si Passenger ne fonctionne pas correctement avec FastAPI, vous pouvez utiliser Gunicorn :

```bash
# Créez un fichier de service systemd
sudo nano /etc/systemd/system/pasci-api.service
```

Contenu du fichier :

```ini
[Unit]
Description=PASCI FastAPI Application
After=network.target

[Service]
User=votre_utilisateur_plesk
Group=psacln
WorkingDirectory=/var/www/vhosts/yourdomain.com/api.yourdomain.com
Environment="PATH=/var/www/vhosts/yourdomain.com/api.yourdomain.com/venv/bin"
ExecStart=/var/www/vhosts/yourdomain.com/api.yourdomain.com/venv/bin/gunicorn -c gunicorn.conf.py app.main:app

[Install]
WantedBy=multi-user.target
```

Activez et démarrez le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable pasci-api
sudo systemctl start pasci-api
sudo systemctl status pasci-api
```

Configurez ensuite un proxy inverse dans Plesk :
1. Allez dans **Apache & nginx Settings**
2. Dans **Additional nginx directives**, ajoutez :

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Étape 1.9 : Tester l'API

Ouvrez votre navigateur et allez sur :
- `https://api.yourdomain.com/docs` - Documentation Swagger
- `https://api.yourdomain.com/redoc` - Documentation ReDoc
- `https://api.yourdomain.com/admin` - Panel d'administration

---

## Partie 2 : Déploiement du Frontend (Next.js)

### Étape 2.1 : Préparer le domaine principal

Le frontend sera déployé sur le domaine principal (`yourdomain.com`)

### Étape 2.2 : Télécharger le code

```bash
# Via SSH
cd /var/www/vhosts/yourdomain.com/httpdocs

# Clonez le repository frontend
git clone https://github.com/votre-utilisateur/pasci-web.git .
```

### Étape 2.3 : Configurer les variables d'environnement

Créez un fichier `.env.local` :

```bash
nano .env.local
```

Ajoutez :

```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NODE_ENV=production
```

### Étape 2.4 : Installer les dépendances et builder

```bash
# Vérifiez que Node.js est installé
node --version
npm --version

# Si Node.js n'est pas installé, installez-le via Plesk Node.js Manager

# Installez les dépendances
npm install

# Buildez l'application pour la production
npm run build
```

### Étape 2.5 : Configurer Node.js dans Plesk

1. Dans Plesk, allez dans votre domaine principal
2. Cliquez sur **Node.js**
3. Configurez :
   - **Mode de l'application** : Production
   - **Version de Node.js** : 18.x ou supérieur
   - **Document Root** : `/httpdocs`
   - **Application Root** : `/httpdocs`
   - **Application Startup File** : `node_modules/next/dist/bin/next`
   - **Arguments** : `start -p 3000`

4. Dans **Environment Variables**, ajoutez :
   ```
   NODE_ENV=production
   NEXT_PUBLIC_API_URL=https://api.yourdomain.com
   ```

5. Cliquez sur **Enable Node.js** et **Restart App**

### Étape 2.6 : Configurer le proxy Nginx

Dans **Apache & nginx Settings**, ajoutez dans **Additional nginx directives** :

```nginx
location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Étape 2.7 : Alternative - Déploiement statique (SSG)

Si votre application Next.js peut être exportée en statique :

```bash
# Modifiez next.config.ts pour activer l'export
# Ajoutez : output: 'export'

# Buildez et exportez
npm run build

# Les fichiers statiques seront dans le dossier 'out'
# Copiez-les dans httpdocs
```

---

## Configuration de la base de données

### Sauvegardes automatiques

1. Dans Plesk, allez dans **Bases de données**
2. Sélectionnez votre base de données
3. Configurez des sauvegardes automatiques

### Gestion des migrations

Lors des mises à jour du code :

```bash
cd /var/www/vhosts/yourdomain.com/api.yourdomain.com
source venv/bin/activate
alembic upgrade head
```

---

## Configuration SSL

1. Dans Plesk, allez dans **SSL/TLS Certificates**
2. Activez **Let's Encrypt**
3. Cochez :
   - Domaine principal
   - www.yourdomain.com
   - api.yourdomain.com
4. Activez **Force HTTPS**

---

## Maintenance et mises à jour

### Mettre à jour le backend

```bash
cd /var/www/vhosts/yourdomain.com/api.yourdomain.com
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart pasci-api  # Si vous utilisez systemd
```

### Mettre à jour le frontend

```bash
cd /var/www/vhosts/yourdomain.com/httpdocs
git pull origin main
npm install
npm run build
# Redémarrez l'application Node.js via Plesk
```

---

## Dépannage

### L'API ne démarre pas

1. Vérifiez les logs :
   ```bash
   tail -f /var/log/plesk-python/error.log
   # ou
   sudo journalctl -u pasci-api -f
   ```

2. Vérifiez les permissions :
   ```bash
   chown -R votre_utilisateur:psacln /var/www/vhosts/yourdomain.com/api.yourdomain.com
   ```

3. Vérifiez la connexion à la base de données :
   ```bash
   psql -h localhost -U db_user -d pascidb
   ```

### Le frontend ne charge pas

1. Vérifiez que Node.js est en cours d'exécution
2. Vérifiez les logs Node.js dans Plesk
3. Testez l'accès direct au port :
   ```bash
   curl http://localhost:3000
   ```

### Erreurs CORS

Vérifiez que `ALLOWED_ORIGINS` dans le fichier `.env` du backend inclut bien votre domaine frontend.

### Base de données inaccessible

1. Vérifiez que PostgreSQL est en cours d'exécution :
   ```bash
   sudo systemctl status postgresql
   ```

2. Vérifiez les paramètres de connexion dans `.env`

3. Vérifiez les permissions de l'utilisateur PostgreSQL

---

## Support

Pour toute question ou problème, consultez :
- Documentation FastAPI : https://fastapi.tiangolo.com/
- Documentation Next.js : https://nextjs.org/docs
- Documentation Plesk : https://docs.plesk.com/

---

**Remarques importantes** :

- Changez TOUJOURS les mots de passe par défaut
- Utilisez des clés secrètes sécurisées
- Activez les sauvegardes automatiques
- Surveillez les logs régulièrement
- Mettez à jour les dépendances de sécurité
