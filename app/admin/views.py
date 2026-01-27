# app/admin/views.py | Admin model views
from sqladmin import ModelView
from app.models.users import User
from app.models.crasc import Crasc, Region, OscType, Osc, News
from app.models.jobs import Jobs
from app.models.key_stats import KeyStats
from app.models.ptf import Ptf, Projet
from app.models.hero import Hero, Team
from app.models.documentation import Documentation


class UserAdmin(ModelView, model=User):
    """Admin view for User model"""
    name = "Utilisateur"
    name_plural = "Utilisateurs"
    icon = "fa-solid fa-user"

    column_list = [
        User.id,
        User.username,
        User.email,
        User.first_name,
        User.last_name,
        User.is_active,
        User.is_staff,
        User.is_superuser,
        User.date_joined,
    ]

    column_searchable_list = [User.username, User.email, User.first_name, User.last_name]
    column_sortable_list = [User.username, User.email, User.date_joined]
    column_default_sort = [(User.date_joined, True)]

    form_excluded_columns = [User.password, User.last_login]

    # Hide password in detail view
    column_details_exclude_list = [User.password]


class CrascAdmin(ModelView, model=Crasc):
    """Admin view for Crasc model"""
    name = "CRASC"
    name_plural = "CRASC"
    icon = "fa-solid fa-building"

    column_list = [
        Crasc.id,
        Crasc.name,
        Crasc.slug,
        Crasc.description,
        Crasc.osc_count,
        Crasc.created_at,
    ]

    column_searchable_list = [Crasc.name, Crasc.description]
    column_sortable_list = [Crasc.name, Crasc.created_at]
    column_default_sort = [(Crasc.created_at, True)]


class RegionAdmin(ModelView, model=Region):
    """Admin view for Region model"""
    name = "Région"
    name_plural = "Régions"
    icon = "fa-solid fa-map"

    column_list = [Region.id, Region.name, Region.slug, Region.crasc_id]
    column_searchable_list = [Region.name]


class OscTypeAdmin(ModelView, model=OscType):
    """Admin view for OscType model"""
    name = "Type OSC"
    name_plural = "Types OSC"
    icon = "fa-solid fa-tags"

    column_list = [OscType.id, OscType.name, OscType.slug, OscType.description]
    column_searchable_list = [OscType.name]


class OscAdmin(ModelView, model=Osc):
    """Admin view for Osc model"""
    name = "OSC"
    name_plural = "OSC"
    icon = "fa-solid fa-users"

    column_list = [
        Osc.id,
        Osc.name,
        Osc.slug,
        Osc.type_id,
        Osc.crasc_id,
        Osc.created_at,
    ]

    column_searchable_list = [Osc.name, Osc.description]
    column_sortable_list = [Osc.name, Osc.created_at]


class NewsAdmin(ModelView, model=News):
    """Admin view for News model"""
    name = "Actualité"
    name_plural = "Actualités"
    icon = "fa-solid fa-newspaper"

    column_list = [
        News.id,
        News.title,
        News.slug,
        News.osc_id,
        News.crasc_id,
        News.created_at,
    ]

    column_searchable_list = [News.title, News.content]
    column_sortable_list = [News.title, News.created_at]
    column_default_sort = [(News.created_at, True)]


class JobAdmin(ModelView, model=Jobs):
    """Admin view for Jobs model"""
    name = "Offre d'emploi"
    name_plural = "Offres d'emploi"
    icon = "fa-solid fa-briefcase"

    column_list = [
        Jobs.id,
        Jobs.title,
        Jobs.employer,
        Jobs.location,
        Jobs.type,
        Jobs.is_expired,
        Jobs.publication_date,
        Jobs.expiration_date,
    ]

    column_searchable_list = [Jobs.title, Jobs.employer, Jobs.location]
    column_sortable_list = [Jobs.title, Jobs.publication_date]
    column_default_sort = [(Jobs.publication_date, True)]


class KeyStatsAdmin(ModelView, model=KeyStats):
    """Admin view for KeyStats model"""
    name = "Chiffre clé"
    name_plural = "Chiffres clés"
    icon = "fa-solid fa-chart-line"

    column_list = [KeyStats.id, KeyStats.name, KeyStats.number]
    column_searchable_list = [KeyStats.name]


class PtfAdmin(ModelView, model=Ptf):
    """Admin view for Ptf model"""
    name = "PTF"
    name_plural = "PTF"
    icon = "fa-solid fa-handshake"

    column_list = [
        Ptf.id,
        Ptf.name,
        Ptf.slug,
        Ptf.description,
    ]

    column_searchable_list = [Ptf.name, Ptf.description]
    column_sortable_list = [Ptf.name]


class ProjetAdmin(ModelView, model=Projet):
    """Admin view for Projet model"""
    name = "Projet"
    name_plural = "Projets"
    icon = "fa-solid fa-diagram-project"

    column_list = [Projet.id, Projet.name, Projet.slug, Projet.ptf_id]
    column_searchable_list = [Projet.name]
    column_sortable_list = [Projet.name]


class TeamAdmin(ModelView, model=Team):
    """Admin view for Team model"""
    name = "Équipe"
    name_plural = "Équipes"
    icon = "fa-solid fa-people-group"

    column_list = [Team.id, Team.name, Team.slug]
    column_searchable_list = [Team.name]
    column_sortable_list = [Team.name]


class HeroAdmin(ModelView, model=Hero):
    """Admin view for Hero model"""
    name = "Héros"
    name_plural = "Héros"
    icon = "fa-solid fa-user-shield"

    column_list = [Hero.id, Hero.name, Hero.slug, Hero.team_id]
    column_searchable_list = [Hero.name]
    column_sortable_list = [Hero.name]


class DocumentationAdmin(ModelView, model=Documentation):
    """Admin view for Documentation model"""
    name = "Document"
    name_plural = "Documents"
    icon = "fa-solid fa-file"

    column_list = [
        Documentation.id,
        Documentation.title,
        Documentation.slug,
        Documentation.category,
        Documentation.file_type,
        Documentation.crasc_id,
        Documentation.osc_id,
        Documentation.created_at,
    ]

    column_searchable_list = [Documentation.title, Documentation.description]
    column_sortable_list = [Documentation.title, Documentation.created_at]
    column_default_sort = [(Documentation.created_at, True)]
