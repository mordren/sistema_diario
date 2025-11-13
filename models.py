# model.py
"""
Modelos de banco de dados para o sistema de análise de reputação.
Usamos herança dinâmica para evitar problemas de inicialização.
"""

from datetime import datetime
from sqlalchemy.orm import relationship
import json

# Não criamos db aqui - será injetado pelo app.py
db = None

def init_models(database):
    """Inicializa os modelos com a instância do banco"""
    global db, Analise, Polemica, Tweet, Fonte
    db = database
    
    # --- MODELOS COM HERANÇA DINÂMICA --- #
    class AnaliseBase:
        def as_dict(self):
            result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
            result["data_analise"] = self.data_analise.isoformat() if self.data_analise else None
            result["polemicas"] = [p.as_dict() for p in self.polemicas]
            result["tweets"] = [t.as_dict() for t in self.tweets]
            result["fontes"] = [f.as_dict() for f in self.fontes]
            return result

    class Analise(db.Model, AnaliseBase):
        __tablename__ = "analises"

        id = db.Column(db.Integer, primary_key=True)
        nome = db.Column(db.String(255), nullable=False)
        cargo_publico = db.Column(db.String(255))
        total_polemicas = db.Column(db.Integer, default=0)
        resumo_analise = db.Column(db.Text)
        risco_reputacao = db.Column(db.String(100))
        data_analise = db.Column(db.DateTime, default=datetime.utcnow)
        fontes_consultadas = db.Column(db.Text)
        tweets_relevantes = db.Column(db.Text)
        raw = db.Column(db.Text)

        polemicas = relationship("Polemica", back_populates="analise", cascade="all, delete-orphan")
        tweets = relationship("Tweet", back_populates="analise", cascade="all, delete-orphan")
        fontes = relationship("Fonte", back_populates="analise", cascade="all, delete-orphan")

    class Polemica(db.Model):
        __tablename__ = "polemicas"

        id = db.Column(db.Integer, primary_key=True)
        analise_id = db.Column(db.Integer, db.ForeignKey("analises.id"))
        titulo = db.Column(db.String(255))
        descricao = db.Column(db.Text)
        impacto = db.Column(db.String(100))
        fonte = db.Column(db.String(255))
        data_publicacao = db.Column(db.String(100))

        analise = relationship("Analise", back_populates="polemicas")

        def as_dict(self):
            return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    class Tweet(db.Model):
        __tablename__ = "tweets"

        id = db.Column(db.Integer, primary_key=True)
        analise_id = db.Column(db.Integer, db.ForeignKey("analises.id"))
        usuario = db.Column(db.String(255))
        conteudo = db.Column(db.Text)
        data = db.Column(db.String(100))
        url = db.Column(db.String(500))

        analise = relationship("Analise", back_populates="tweets")

        def as_dict(self):
            return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    class Fonte(db.Model):
        __tablename__ = "fontes"

        id = db.Column(db.Integer, primary_key=True)
        analise_id = db.Column(db.Integer, db.ForeignKey("analises.id"))
        titulo = db.Column(db.String(255))
        url = db.Column(db.String(500))
        tipo = db.Column(db.String(100))

        analise = relationship("Analise", back_populates="fontes")

        def as_dict(self):
            return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    # Tornar as classes disponíveis globalmente
    globals()['Analise'] = Analise
    globals()['Polemica'] = Polemica
    globals()['Tweet'] = Tweet
    globals()['Fonte'] = Fonte
    
    print("✅ Modelos inicializados com sucesso")
    return db

def save_analysis(analise_dict: dict):
    """Salva resultado de análise no banco."""
    if db is None:
        raise RuntimeError("Banco não inicializado. Chame init_models primeiro.")
    
    nome = analise_dict.get("nome")
    cargo_publico = analise_dict.get("cargo_publico")
    total_polemicas = analise_dict.get("total_polemicas", 0)
    resumo = analise_dict.get("resumo_analise", "")
    risco = analise_dict.get("risco_reputacao", "")
    fontes = analise_dict.get("fontes_consultadas", [])
    tweets = analise_dict.get("tweets_relevantes", [])
    data_str = analise_dict.get("data_analise")
    data_analise = datetime.fromisoformat(data_str) if data_str else datetime.utcnow()

    analise = Analise(
        nome=nome,
        cargo_publico=cargo_publico,
        total_polemicas=total_polemicas,
        resumo_analise=resumo,
        risco_reputacao=risco,
        data_analise=data_analise,
        fontes_consultadas=json.dumps(fontes, ensure_ascii=False),
        tweets_relevantes=json.dumps(tweets, ensure_ascii=False),
        raw=json.dumps(analise_dict, ensure_ascii=False)
    )

    for p in analise_dict.get("polemicas", []):
        analise.polemicas.append(Polemica(
            titulo=p.get("titulo"),
            descricao=p.get("descricao"),
            impacto=p.get("impacto"),
            fonte=p.get("fonte"),
            data_publicacao=p.get("data_publicacao")
        ))

    db.session.add(analise)
    db.session.commit()
    return analise.id

def get_analysis(id_or_name):
    """Recupera análise completa por ID ou nome."""
    if db is None:
        raise RuntimeError("Banco não inicializado. Chame init_models primeiro.")
    
    analise = None
    if str(id_or_name).isdigit():
        analise = Analise.query.get(int(id_or_name))
    else:
        analise = Analise.query.filter_by(nome=id_or_name).order_by(Analise.id.desc()).first()

    return analise.as_dict() if analise else None