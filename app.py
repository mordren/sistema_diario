# app.py
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
import traceback

import buscar  # seu módulo de análise

# Configuração
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///analises.db")
DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
PORT = int(os.environ.get("FLASK_PORT", "5000"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- Inicialização dos Modelos ---
models_available = False
try:
    import models
    # Inicializa os modelos com a instância do db
    models.init_models(db)
    models_available = True
    print("✅ Models carregados e inicializados com sucesso")
except Exception as e:
    print(f"❌ Erro ao carregar models: {e}")
    models_available = False

# --- Rotas (mantenha as mesmas que você tinha) ---
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analises")
def listar_analises():
    if not models_available:
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
    if not models_available:
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
        return jsonify({"error": "Enviar JSON com campo 'nome'."}), 400

    nome = data.get("nome")
    cargo = data.get("cargo")

    try:
        resultado = buscar.executar_analise(nome, cargo)
        print(f"✅ Análise executada, total polêmicas: {resultado.get('total_polemicas', 0)}")
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return jsonify({"error": str(e)}), 500

    # Tentar salvar no banco
    if models_available:
        try:
            ident = models.save_analysis(resultado)
            print(f"✅ Análise salva no banco com ID: {ident}")
            return jsonify({
                "status": "ok", 
                "saved": True,
                "id": ident,
                "analise": resultado
            }), 201
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
            # Fallback para JSON
            filename = f"analise_fallback_{nome}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
            return jsonify({
                "status": "ok",
                "saved": False,
                "reason": f"Erro no banco: {e} - Salvo em {filename}",
                "analise": resultado
            }), 201
    else:
        return jsonify({
            "status": "ok",
            "saved": False,
            "reason": "Models não disponível",
            "analise": resultado
        }), 201

@app.route("/api/analises/<ident>")
def obter_analise_api(ident):
    """Retorna uma análise (API)."""
    if models_available:
        analise = models.get_analysis(ident)
        if analise:
            return jsonify(analise)
        return jsonify({"error": "Análise não encontrada."}), 404

    # Fallback: tentar JSON
    files = [f for f in os.listdir() if f.startswith(f"analise_completa_{ident}")]
    if files:
        path = files[-1]
        return send_file(path, mimetype="application/json")
    return jsonify({"error": "Análise não encontrada."}), 404

# Comando para criar o banco
@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas do banco"""
    try:
        with app.app_context():
            db.create_all()
        print("✅ Tabelas criadas com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")

if __name__ == "__main__":
    # Garantir que as tabelas existam
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        print(f"Aviso: {e}")
    
    print(f"🚀 Servidor iniciando...")
    app.run(host=HOST, port=PORT, debug=DEBUG)