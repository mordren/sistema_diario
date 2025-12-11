# schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PolemicaSchema(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    gravidade: Optional[str] = None
    categoria: Optional[str] = None
    fonte_url: Optional[str] = None

class EmpresaAssociadaSchema(BaseModel):
    nome_empresa: str
    cnpj: Optional[str] = None
    relacao: Optional[str] = None
    fonte_url: Optional[str] = None

class AnalisePessoaSchema(BaseModel):
    nome: str
    cargo: Optional[str] = None
    resumo_analise: Optional[str] = None
    polemicas: List[PolemicaSchema] = []
    empresas_associadas: List[EmpresaAssociadaSchema] = []
    risco_reputacao: Optional[str] = None
    recomendacoes: Optional[str] = None
    tweets_relevantes: List[str] = []
    fontes_consultadas: List[str] = []
    data_analise: Optional[datetime] = None