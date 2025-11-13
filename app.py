import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# ========== CONFIGURAÇÃO RENDER ==========
# O Render automaticamente fornece DATABASE_URL para PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///analises.db')

# Se estiver usando PostgreSQL, pode precisar ajustar a URL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

print(f"🔗 Conectando ao banco: {DATABASE_URL[:50]}...")  # Log parcial da URL

# ========== IMPORTAR MÓDULOS ==========
print("🔄 Carregando módulos...")

# Importar buscar.py
try:
    import buscar
    BUSCAR_AVAILABLE = True
    print("✅ buscar.py carregado com sucesso")
except Exception as e:
    print(f"❌ Erro ao carregar buscar.py: {e}")
    BUSCAR_AVAILABLE = False

# Importar e inicializar modelos
try:
    import models
    models.init_models(db)
    MODELS_AVAILABLE = True
    print("✅ Models inicializados com sucesso")
except Exception as e:
    print(f"❌ Erro nos models: {e}")
    MODELS_AVAILABLE = False

# ========== ROTAS (mantenha suas rotas existentes) ==========
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analises")
def listar_analises():
    if not MODELS_AVAILABLE:
        return render_template("listar_analises.html", analises=[])
    
    try:
        from models import Analise
        analises = Analise.query.order_by(Analise.data_analise.desc()).all()
        return render_template("listar_analises.html", analises=analises)
    except Exception as e:
        print(f"Erro ao listar análises: {e}")
        return render_template("listar_analises.html", analises=[])

@app.route("/analises/<ident>")
def detalhar_analise(ident):
    if not MODELS_AVAILABLE:
        return render_template("analise_detalhe.html", analise=None)
    
    try:
        analise = models.get_analysis(ident)
        if analise:
            # Converter campos JSON para listas
            if isinstance(analise.get("fontes_consultadas"), str):
                analise["fontes_consultadas"] = json.loads(analise["fontes_consultadas"])
            if isinstance(analise.get("tweets_relevantes"), str):
                analise["tweets_relevantes"] = json.loads(analise["tweets_relevantes"])
        return render_template("analise_detalhe.html", analise=analise)
    except Exception as e:
        print(f"Erro ao detalhar análise: {e}")
        return render_template("analise_detalhe.html", analise=None)

@app.route("/api/analises", methods=["POST"])
def criar_analise():
    data = request.get_json(force=True, silent=True)
    if not data or "nome" not in data:
        return jsonify({"error": "Campo 'nome' é obrigatório"}), 400

    nome = data.get("nome")
    cargo = data.get("cargo")

    try:
        # Usa buscar.py se disponível, senão usa fallback
        if BUSCAR_AVAILABLE:
            resultado = buscar.executar_analise(nome, cargo)
            tipo_busca = "real"
            print(f"✅ Busca REAL executada para: {nome}")
        else:
            from datetime import datetime
            resultado = {
                "nome": nome,
                "cargo_publico": cargo,
                "total_polemicas": 2,
                "resumo_analise": f"Análise de demonstração para {nome}",
                "risco_reputacao": "medio",
                "polemicas": [
                    {
                        "titulo": "Sistema em Operação",
                        "descricao": "Funcionalidade de busca em configuração",
                        "impacto": "baixo",
                        "fonte": "Sistema",
                        "data_publicacao": datetime.now().strftime("%Y-%m-%d")
                    }
                ],
                "fontes_consultadas": ["Sistema de análise"],
                "tweets_relevantes": [],
                "data_analise": datetime.now().isoformat()
            }
            tipo_busca = "demonstração"
            print(f"✅ Busca DEMONSTRAÇÃO executada para: {nome}")
            
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return jsonify({"error": str(e)}), 500

    # Salvar no banco
    if MODELS_AVAILABLE:
        try:
            ident = models.save_analysis(resultado)
            print(f"✅ Análise salva no banco com ID: {ident}")
            return jsonify({
                "status": "ok", 
                "saved": True,
                "id": ident,
                "tipo_busca": tipo_busca,
                "analise": resultado
            }), 201
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
            return jsonify({
                "status": "ok",
                "saved": False,
                "reason": f"Erro no banco: {e}",
                "analise": resultado
            }), 201
    else:
        return jsonify({
            "status": "ok",
            "saved": False,
            "reason": "Models não disponível",
            "analise": resultado
        }), 201

# ========== INICIALIZAÇÃO DO BANCO ==========
def init_database():
    """Inicializa o banco de dados"""
    try:
        with app.app_context():
            db.create_all()
            print("✅ Tabelas do banco verificadas/criadas")
            
            # Verificar se consegue conectar
            from models import Analise
            count = Analise.query.count()
            print(f"📊 Total de análises no banco: {count}")
            
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
"""
if __name__ == "__main__":
    # Garantir que as tabelas existam
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        print(f"Aviso: {e}")
    
    print(f"🚀 Servidor iniciando...")
    app.run(host=HOST, port=PORT, debug=DEBUG)
"""

# ========== CONFIGURAÇÃO RENDER ==========
if __name__ == "__main__":
    # Inicializar banco
    init_database()
    
    # Configuração Render
    port = int(os.environ.get("PORT", 10000))
    host = "0.0.0.0"
    
    print(f"🚀 Servidor iniciando no Render...")
    print(f"📍 Host: {host}")
    print(f"🔌 Porta: {port}")
    print(f"🌐 Acesse: http://{host}:{port}")
    print(f"🔗 Banco: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'SQLite'}")
    
    app.run(host=host, port=port, debug=DEBUG)