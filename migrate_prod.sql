-- ============================================================
-- Migration production PASCI
-- À exécuter via : psql -U pasci_user -d pasci_db -f migrate_prod.sql
-- ============================================================

-- 1. Colonnes manquantes sur la table formations
ALTER TABLE formations ADD COLUMN IF NOT EXISTS type VARCHAR(20) DEFAULT 'gratuite';
ALTER TABLE formations ADD COLUMN IF NOT EXISTS price FLOAT;

-- 2. Colonnes manquantes sur formation_inscription (paiement)
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) DEFAULT 'gratuite';
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS payment_transaction_id VARCHAR(100);
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS payment_amount FLOAT;
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS payment_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS payment_operator VARCHAR(100);

-- Contrainte unique sur transaction_id (si pas déjà présente)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'formation_inscription_payment_transaction_id_key'
  ) THEN
    ALTER TABLE formation_inscription
      ADD CONSTRAINT formation_inscription_payment_transaction_id_key
      UNIQUE (payment_transaction_id);
  END IF;
END $$;

-- 3. Table formation_rubrique
CREATE TABLE IF NOT EXISTS formation_rubrique (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    slug VARCHAR(150) UNIQUE,
    description TEXT,
    color VARCHAR(20) DEFAULT '#E05017',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Colonne rubrique_id sur formations
ALTER TABLE formations ADD COLUMN IF NOT EXISTS rubrique_id INTEGER REFERENCES formation_rubrique(id) ON DELETE SET NULL;

-- 4. Table formation_module
CREATE TABLE IF NOT EXISTS formation_module (
    id SERIAL PRIMARY KEY,
    formation_id INTEGER NOT NULL REFERENCES formations(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 5. Table formation_lecon
CREATE TABLE IF NOT EXISTS formation_lecon (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES formation_module(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    type VARCHAR(20) DEFAULT 'text',
    content TEXT,
    file_path VARCHAR(500),
    duration_minutes INTEGER,
    is_preview BOOLEAN DEFAULT FALSE,
    "order" INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 6. Table certificat
CREATE TABLE IF NOT EXISTS certificat (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    inscription_id INTEGER NOT NULL REFERENCES formation_inscription(id) ON DELETE CASCADE,
    formation_title VARCHAR(250) NOT NULL,
    participant_name VARCHAR(200) NOT NULL,
    participant_email VARCHAR(255) NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_certificat_code ON certificat(code);

-- 7. Table formation_avis
CREATE TABLE IF NOT EXISTS formation_avis (
    id SERIAL PRIMARY KEY,
    formation_id INTEGER NOT NULL REFERENCES formations(id) ON DELETE CASCADE,
    inscription_id INTEGER NOT NULL UNIQUE REFERENCES formation_inscription(id) ON DELETE CASCADE,
    participant_name VARCHAR(200) NOT NULL,
    note INTEGER NOT NULL CHECK (note BETWEEN 1 AND 5),
    commentaire TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_formation_avis_formation ON formation_avis(formation_id);

-- 8. Table formation_progression
CREATE TABLE IF NOT EXISTS formation_progression (
    id SERIAL PRIMARY KEY,
    inscription_id INTEGER NOT NULL REFERENCES formation_inscription(id) ON DELETE CASCADE,
    lecon_id INTEGER NOT NULL REFERENCES formation_lecon(id) ON DELETE CASCADE,
    viewed_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(inscription_id, lecon_id)
);
CREATE INDEX IF NOT EXISTS ix_formation_progression_inscription ON formation_progression(inscription_id);

-- 9. Nouvelles colonnes sur pole_concertation (migration d4e5f6a7b8c9)
ALTER TABLE pole_concertation ADD COLUMN IF NOT EXISTS objectifs_annuels TEXT;
ALTER TABLE pole_concertation ADD COLUMN IF NOT EXISTS nb_osc_membres INTEGER;
ALTER TABLE pole_concertation ADD COLUMN IF NOT EXISTS regions_influence TEXT;
ALTER TABLE pole_concertation ADD COLUMN IF NOT EXISTS realisations TEXT;
ALTER TABLE pole_concertation ADD COLUMN IF NOT EXISTS agenda TEXT;

-- 10. is_redacteur sur user + statut_publication sur les contenus (migration f1a2b3c4d5e6)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_redacteur BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE news ADD COLUMN IF NOT EXISTS statut_publication VARCHAR(20) NOT NULL DEFAULT 'publie';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS statut_publication VARCHAR(20) NOT NULL DEFAULT 'publie';
ALTER TABLE formations ADD COLUMN IF NOT EXISTS statut_publication VARCHAR(20) NOT NULL DEFAULT 'publie';
ALTER TABLE offreprojet ADD COLUMN IF NOT EXISTS statut_publication VARCHAR(20) NOT NULL DEFAULT 'publie';

-- 11. Table numero_utile (migration e5f6a7b8c9d0)
CREATE TABLE IF NOT EXISTS numero_utile (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(150) NOT NULL,
    numero VARCHAR(50) NOT NULL,
    description TEXT,
    categorie VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    ordre INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 12. Colonnes manquantes sur la table ptf
ALTER TABLE ptf ADD COLUMN IF NOT EXISTS categorie VARCHAR(100);
ALTER TABLE ptf ADD COLUMN IF NOT EXISTS exigences_majeures TEXT;
ALTER TABLE ptf ADD COLUMN IF NOT EXISTS nature_relations TEXT;

-- 13. Colonnes manquantes sur la table jobs
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS missions TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS requirements TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS benefits TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS publication_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expiration_date TIMESTAMP WITH TIME ZONE;

-- 14. Colonnes manquantes sur la table formations
ALTER TABLE formations ADD COLUMN IF NOT EXISTS categorie VARCHAR(200);

-- 15. Colonnes manquantes sur formation_inscription
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS payment_notify_token VARCHAR(500);
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS participant_nom VARCHAR(100);
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS participant_prenoms VARCHAR(150);
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS participant_phone VARCHAR(30);
ALTER TABLE formation_inscription ADD COLUMN IF NOT EXISTS categorie_acteur VARCHAR(100);

-- 16. Colonnes manquantes sur la table demande_adhesion
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS sigle VARCHAR(100);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS departement VARCHAR(150);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS sous_prefecture VARCHAR(150);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS origine_organisation VARCHAR(50);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS type_document_formalisation VARCHAR(50);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS document_formalisation_path VARCHAR(2048);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS existence_siege BOOLEAN;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS categorie VARCHAR(100);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS niveau_regroupement VARCHAR(30);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS domaine_prioritaire VARCHAR(200);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS domaine_prioritaire_2 VARCHAR(200);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS domaine_prioritaire_3 VARCHAR(200);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS domaine_prioritaire_4 VARCHAR(200);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS domaine_prioritaire_5 VARCHAR(200);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_membres INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_femmes_membres INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_hommes_membres INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_membres_jeunes INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_membres_handicap INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_membres_be INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nombre_mandats_be INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS duree_mandat_be VARCHAR(100);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_beneficiaires INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_femmes_beneficiaires INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_jeunes_beneficiaires INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS nb_beneficiaires_handicap INTEGER;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS adhesion_crasc_statut VARCHAR(20);
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS organes_gouvernance TEXT;
ALTER TABLE demande_adhesion ADD COLUMN IF NOT EXISTS osc_id INTEGER REFERENCES osc(id) ON DELETE SET NULL;

-- 17. Colonnes manquantes sur la table offreprojet
ALTER TABLE offreprojet ADD COLUMN IF NOT EXISTS ptf_id INTEGER REFERENCES ptf(id) ON DELETE SET NULL;
ALTER TABLE offreprojet ADD COLUMN IF NOT EXISTS offre_url VARCHAR(500);

-- 18. Colonnes manquantes sur la table numero_utile (label au lieu de nom)
ALTER TABLE numero_utile ADD COLUMN IF NOT EXISTS label VARCHAR(200);
UPDATE numero_utile SET label = nom WHERE label IS NULL AND nom IS NOT NULL;

-- 19. Nouvelles tables manquantes
CREATE TABLE IF NOT EXISTS annonce (
    id SERIAL PRIMARY KEY,
    texte VARCHAR(500) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    ordre INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hero_slide (
    id SERIAL PRIMARY KEY,
    image_path VARCHAR(500) NOT NULL,
    ordre INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS faq (
    id SERIAL PRIMARY KEY,
    question VARCHAR(300) NOT NULL,
    answer TEXT NOT NULL,
    ordre INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS site_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(120) UNIQUE,
    description VARCHAR(500),
    color VARCHAR(7) DEFAULT '#3B82F6',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS news_tags (
    news_id INTEGER NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (news_id, tag_id)
);

CREATE TABLE IF NOT EXISTS catalogue_formation (
    id SERIAL PRIMARY KEY,
    titre VARCHAR(200) NOT NULL,
    description TEXT,
    fichier_path VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 20. Colonnes manquantes sur la table osc
ALTER TABLE osc ADD COLUMN IF NOT EXISTS sigle VARCHAR(100);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS region_nom VARCHAR(150);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS departement VARCHAR(150);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS sous_prefecture VARCHAR(150);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS origine_organisation VARCHAR(50);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS document_formalisation_path VARCHAR(2048);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS plan_action_document_path VARCHAR(2048);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS rapports_annuels_document_path VARCHAR(2048);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS domaine_prioritaire_5 VARCHAR(200);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nb_hommes_membres INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nb_membres_handicap INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nombre_mandats_be INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nb_cdi INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nb_cdd INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nb_femmes_beneficiaires INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nb_jeunes_beneficiaires INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS nb_beneficiaires_handicap INTEGER;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS date_derniere_activite VARCHAR(30);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS date_designation_responsable VARCHAR(30);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS date_prochaine_designation VARCHAR(30);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS adhesion_crasc_statut VARCHAR(20);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS adhesion_crasc_document_path VARCHAR(2048);
ALTER TABLE osc ADD COLUMN IF NOT EXISTS organes_gouvernance TEXT;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS pays_couverture TEXT;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS plan_action_annee_cours BOOLEAN;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS plan_action_annee_cours_details TEXT;
ALTER TABLE osc ADD COLUMN IF NOT EXISTS recommandations_2 TEXT;

-- 21. Champ type sur hero_slide (séparation slides haut / partenaires bas)
ALTER TABLE hero_slide ADD COLUMN IF NOT EXISTS type VARCHAR(20) DEFAULT 'haut';

-- 22. Visibilité OSC dans l'annuaire public
ALTER TABLE osc ADD COLUMN IF NOT EXISTS is_visible BOOLEAN DEFAULT TRUE;

-- 23. Synchroniser le champ categorie avec le nom de la rubrique sur les formations existantes
UPDATE formations f
SET categorie = fr.name
FROM formation_rubrique fr
WHERE f.rubrique_id = fr.id
  AND (f.categorie IS NULL OR f.categorie != fr.name);

-- 24. Paiement manuel dons : colonne operateur sur don
ALTER TABLE don ADD COLUMN IF NOT EXISTS operateur VARCHAR(50);

-- 25. Notifications internes + modération des ressources documentaires
ALTER TABLE documentation ADD COLUMN IF NOT EXISTS statut_publication VARCHAR(20) DEFAULT 'publie';

CREATE TABLE IF NOT EXISTS notification (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'info',
    link_url VARCHAR(500),
    is_read BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_notification_user_id ON notification(user_id);
CREATE INDEX IF NOT EXISTS ix_notification_is_read ON notification(is_read);

-- ============================================================
SELECT 'Migration terminée avec succès' AS status;
-- ============================================================
