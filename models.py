

from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Criar instância do SQLAlchemy sem inicializar com app ainda
db = SQLAlchemy()

Base = declarative_base()

# ========== MODELOS DO BANCO ==========

class GravidadeEnum(str, Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

class TipoFonteEnum(str, Enum):
    TWITTER = "twitter"
    NOTICIA = "noticia"
    FORUM = "forum"
    BLOG = "blog"
    SITE_OFICIAL = "site_oficial"

# models.py

class AnalisePessoaDB(db.Model):
    __tablename__ = 'analise_pessoa'

    id = db.Column(db.Integer, primary_key=True, index=True)
    nome = db.Column(db.String, nullable=False)
    cargo = db.Column(db.String, nullable=True)
    data_analise = db.Column(db.DateTime, default=datetime.utcnow)
    fontes_consultadas = db.Column(db.Text, nullable=True)
    resumo_analise = db.Column(db.Text, nullable=True)
    risco_reputacao = db.Column(db.String, nullable=True)
    recomendacoes = db.Column(db.Text, nullable=True)
    tweets_relevantes = db.Column(db.Text, nullable=True)
    total_polemicas = db.Column(db.Integer, default=0)

    # Relacionamentos
    polemicas = db.relationship("PolemicaDB", back_populates="analise_pessoa", cascade="all, delete-orphan")
    empresas_associadas = db.relationship("EmpresaAssociadaDB", back_populates="analise_pessoa", cascade="all, delete-orphan")

class PolemicaDB(db.Model):
    __tablename__ = 'polemica'

    id = db.Column(db.Integer, primary_key=True, index=True)
    analise_pessoa_id = db.Column(db.Integer, db.ForeignKey('analise_pessoa.id'))
    titulo = db.Column(db.String, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    gravidade = db.Column(db.String, nullable=True)
    categoria = db.Column(db.String, nullable=True)
    fonte_url = db.Column(db.String, nullable=True)

    analise_pessoa = db.relationship("AnalisePessoaDB", back_populates="polemicas")

class EmpresaAssociadaDB(db.Model):
    __tablename__ = 'empresa_associada'

    id = db.Column(db.Integer, primary_key=True, index=True)
    analise_pessoa_id = db.Column(db.Integer, db.ForeignKey('analise_pessoa.id'))
    nome_empresa = db.Column(db.String, nullable=False)
    cnpj = db.Column(db.String, nullable=True)
    relacao = db.Column(db.String, nullable=True)
    fonte_url = db.Column(db.String, nullable=True)

    analise_pessoa = db.relationship("AnalisePessoaDB", back_populates="empresas_associadas")

class Polemica(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    gravidade: Optional[str] = None
    categoria: Optional[str] = None
    fonte_url: Optional[str] = None

class EmpresaAssociada(BaseModel):
    nome_empresa: str
    cnpj: Optional[str] = None
    relacao: Optional[str] = None
    fonte_url: Optional[str] = None

class AnalisePessoa(BaseModel):
    resumo_analise: Optional[str] = None
    polemicas: List[Polemica] = []
    empresas_associadas: List[EmpresaAssociada] = []
    risco_reputacao: Optional[str] = None
    recomendacoes: Optional[str] = None
    tweets_relevantes: List[str] = []

class AnalisePessoaCreate(BaseModel):
    nome: str
    cargo: Optional[str] = None
    data_analise: datetime
    fontes_consultadas: Optional[str] = None
    resumo_analise: Optional[str] = None
    risco_reputacao: Optional[str] = None
    recomendacoes: Optional[str] = None
    tweets_relevantes: Optional[str] = None
    total_polemicas: int = 0

class PolemicaCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    gravidade: Optional[str] = None
    categoria: Optional[str] = None
    fonte_url: Optional[str] = None

class EmpresaAssociadaCreate(BaseModel):
    nome_empresa: str
    cnpj: Optional[str] = None
    relacao: Optional[str] = None
    fonte_url: Optional[str] = None

def init_models(db_instance):    
    Base.metadata.bind = db_instance.engine
    Base.metadata.create_all(db_instance.engine)