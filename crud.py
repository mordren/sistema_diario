# crud.py
from sqlalchemy.orm import Session
from typing import List, Optional
from models import (
    AnalisePessoaDB, PolemicaDB, EmpresaAssociadaDB,
    AnalisePessoaCreate, PolemicaCreate, EmpresaAssociadaCreate,
    AnalisePessoa, Polemica, EmpresaAssociada
)

# CRUD para AnalisePessoa
def create_analise_pessoa(db: Session, analise: AnalisePessoaCreate) -> AnalisePessoaDB:
    db_analise = AnalisePessoaDB(**analise.dict())
    db.add(db_analise)
    db.commit()
    db.refresh(db_analise)
    return db_analise

def get_analise_pessoa(db: Session, analise_id: int) -> Optional[AnalisePessoaDB]:
    return db.query(AnalisePessoaDB).filter(AnalisePessoaDB.id == analise_id).first()

def get_analise_pessoa_by_nome(db: Session, nome: str) -> Optional[AnalisePessoaDB]:
    return db.query(AnalisePessoaDB).filter(AnalisePessoaDB.nome == nome).first()

def get_all_analise_pessoas(db: Session, skip: int = 0, limit: int = 100) -> List[AnalisePessoaDB]:
    return db.query(AnalisePessoaDB).offset(skip).limit(limit).all()

def update_analise_pessoa(db: Session, analise_id: int, analise_update: AnalisePessoaCreate) -> Optional[AnalisePessoaDB]:
    db_analise = db.query(AnalisePessoaDB).filter(AnalisePessoaDB.id == analise_id).first()
    if db_analise:
        for field, value in analise_update.dict().items():
            setattr(db_analise, field, value)
        db.commit()
        db.refresh(db_analise)
    return db_analise

def delete_analise_pessoa(db: Session, analise_id: int) -> bool:
    db_analise = db.query(AnalisePessoaDB).filter(AnalisePessoaDB.id == analise_id).first()
    if db_analise:
        db.delete(db_analise)
        db.commit()
        return True
    return False

# CRUD para Polemica
def create_polemica(db: Session, polemica: PolemicaCreate, analise_pessoa_id: int) -> PolemicaDB:
    db_polemica = PolemicaDB(**polemica.dict(), analise_pessoa_id=analise_pessoa_id)
    db.add(db_polemica)
    
    # Atualiza o total de polêmicas da pessoa
    analise_pessoa = db.query(AnalisePessoaDB).filter(AnalisePessoaDB.id == analise_pessoa_id).first()
    if analise_pessoa:
        analise_pessoa.total_polemicas += 1
    
    db.commit()
    db.refresh(db_polemica)
    return db_polemica

def get_polemica(db: Session, polemica_id: int) -> Optional[PolemicaDB]:
    return db.query(PolemicaDB).filter(PolemicaDB.id == polemica_id).first()

def get_polemicas_by_analise_pessoa(db: Session, analise_pessoa_id: int) -> List[PolemicaDB]:
    return db.query(PolemicaDB).filter(PolemicaDB.analise_pessoa_id == analise_pessoa_id).all()

def update_polemica(db: Session, polemica_id: int, polemica_update: PolemicaCreate) -> Optional[PolemicaDB]:
    db_polemica = db.query(PolemicaDB).filter(PolemicaDB.id == polemica_id).first()
    if db_polemica:
        for field, value in polemica_update.dict().items():
            setattr(db_polemica, field, value)
        db.commit()
        db.refresh(db_polemica)
    return db_polemica

def delete_polemica(db: Session, polemica_id: int) -> bool:
    db_polemica = db.query(PolemicaDB).filter(PolemicaDB.id == polemica_id).first()
    if db_polemica:
        # Atualiza o total de polêmicas da pessoa
        analise_pessoa = db.query(AnalisePessoaDB).filter(AnalisePessoaDB.id == db_polemica.analise_pessoa_id).first()
        if analise_pessoa and analise_pessoa.total_polemicas > 0:
            analise_pessoa.total_polemicas -= 1
        
        db.delete(db_polemica)
        db.commit()
        return True
    return False

# CRUD para EmpresaAssociada
def create_empresa_associada(db: Session, empresa: EmpresaAssociadaCreate, analise_pessoa_id: int) -> EmpresaAssociadaDB:
    db_empresa = EmpresaAssociadaDB(**empresa.dict(), analise_pessoa_id=analise_pessoa_id)
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

def get_empresa_associada(db: Session, empresa_id: int) -> Optional[EmpresaAssociadaDB]:
    return db.query(EmpresaAssociadaDB).filter(EmpresaAssociadaDB.id == empresa_id).first()

def get_empresas_by_analise_pessoa(db: Session, analise_pessoa_id: int) -> List[EmpresaAssociadaDB]:
    return db.query(EmpresaAssociadaDB).filter(EmpresaAssociadaDB.analise_pessoa_id == analise_pessoa_id).all()

def update_empresa_associada(db: Session, empresa_id: int, empresa_update: EmpresaAssociadaCreate) -> Optional[EmpresaAssociadaDB]:
    db_empresa = db.query(EmpresaAssociadaDB).filter(EmpresaAssociadaDB.id == empresa_id).first()
    if db_empresa:
        for field, value in empresa_update.dict().items():
            setattr(db_empresa, field, value)
        db.commit()
        db.refresh(db_empresa)
    return db_empresa

def delete_empresa_associada(db: Session, empresa_id: int) -> bool:
    db_empresa = db.query(EmpresaAssociadaDB).filter(EmpresaAssociadaDB.id == empresa_id).first()
    if db_empresa:
        db.delete(db_empresa)
        db.commit()
        return True
    return False

# Operações complexas/agregadas
def get_complete_analise_pessoa(db: Session, analise_id: int) -> Optional[AnalisePessoaDB]:
    return db.query(AnalisePessoaDB)\
        .filter(AnalisePessoaDB.id == analise_id)\
        .options(
            db.joinedload(AnalisePessoaDB.polemicas),
            db.joinedload(AnalisePessoaDB.empresas_associadas)
        )\
        .first()

def create_complete_analise_pessoa(
    db: Session, 
    analise: AnalisePessoaCreate,
    polemicas: List[PolemicaCreate] = None,
    empresas: List[EmpresaAssociadaCreate] = None
) -> AnalisePessoaDB:
    # Cria a análise base
    db_analise = create_analise_pessoa(db, analise)
    
    # Adiciona polêmicas se fornecidas
    if polemicas:
        for polemica in polemicas:
            create_polemica(db, polemica, db_analise.id)
    
    # Adiciona empresas se fornecidas
    if empresas:
        for empresa in empresas:
            create_empresa_associada(db, empresa, db_analise.id)
    
    # Atualiza o total de polêmicas
    if polemicas:
        db_analise.total_polemicas = len(polemicas)
        db.commit()
        db.refresh(db_analise)
    
    return db_analise

# Buscas e filtros
def search_analise_pessoas_by_nome(db: Session, nome: str) -> List[AnalisePessoaDB]:
    return db.query(AnalisePessoaDB)\
        .filter(AnalisePessoaDB.nome.ilike(f"%{nome}%"))\
        .all()

def get_analises_by_gravidade(db: Session, gravidade: str) -> List[AnalisePessoaDB]:
    return db.query(AnalisePessoaDB)\
        .filter(AnalisePessoaDB.risco_reputacao == gravidade)\
        .all()

def get_polemicas_by_gravidade(db: Session, gravidade: str) -> List[PolemicaDB]:
    return db.query(PolemicaDB)\
        .filter(PolemicaDB.gravidade == gravidade)\
        .all()