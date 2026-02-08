# models/documentation.py | Documentation model
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, DateTime, func, TEXT, ForeignKey, Integer
from typing import Optional
import slugify


class Documentation(SQLModel, table=True):
    """
    Représente un document dans la base de données.
    Peut être de type 'documentation' ou 'fiche'.
    """
    title: str = Field(index=True, unique=True, description="Titre du document.")
    description: Optional[str] = Field(
        sa_column=Column(TEXT, nullable=True),
        description="Description du document."
    )
    type: str = Field(
        default="documentation",
        nullable=False,
        max_length=50,
        description="Type de ressource: 'documentation' ou 'fiche'."
    )
    category: Optional[str] = Field(
        default=None,
        nullable=True,
        max_length=100,
        description="Catégorie du document (Rapport, Guide, Étude, Manuel, PV, Infographie, Politique, Récit, Plan)."
    )
    file_path: Optional[str] = Field(
        default=None, 
        nullable=True, 
        max_length=2048,
        description="Chemin du fichier document (PDF, DOCX, etc.)."
    )
    file_type: Optional[str] = Field(
        default=None,
        nullable=True,
        max_length=50,
        description="Type de fichier (pdf, docx, xlsx, etc.)."
    )
    file_size: Optional[int] = Field(
        default=None,
        nullable=True,
        description="Taille du fichier en octets."
    )
    thumbnail_path: Optional[str] = Field(
        default="default.png", 
        nullable=True, 
        max_length=2048,
        description="Chemin de l'image de couverture."
    )
    
    # Relations optionnelles
    crasc_id: Optional[int] = Field(
        default=None, 
        nullable=True, 
        foreign_key="crasc.id", 
        ondelete="SET NULL"
    )
    crasc: Optional["Crasc"] = Relationship(back_populates="documents")
    
    osc_id: Optional[int] = Field(
        default=None, 
        nullable=True, 
        foreign_key="osc.id", 
        ondelete="SET NULL"
    )
    osc: Optional["Osc"] = Relationship(back_populates="documents")

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: Optional[str] = Field(default=None, nullable=True, max_length=100, unique=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now()),
    )

    # Création automatique de slug
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.title and not self.slug:
            self.slug = slugify.slugify(self.title)
    
    # Representation in admin/logs
    def __repr__(self) -> str:
        return f"<Document: {self.title}>"
