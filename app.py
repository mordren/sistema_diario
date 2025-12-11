# app.py - ATUALIZAR A CONFIGURAÇÃO DO BANCO
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template


load_dotenv()
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL não configurada! Configure a variável de ambiente DATABASE_URL.")

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

print(f"🔗 Conectando ao PostgreSQL: {DATABASE_URL}")


# ========== IMPORTAR MÓDULOS ==========
print("📄 Carregando módulos...")

# Importar db dos models primeiro
from models import db
# Inicializar db com a app
db.init_app(app)

MODELS_AVAILABLE = False
BUSCAR_AVAILABLE = False

try:
    from models import AnalisePessoaDB, PolemicaDB, EmpresaAssociadaDB
    MODELS_AVAILABLE = True
    print("✅ Models carregados com sucesso")
except Exception as e:
    print(f"❌ Erro nos models: {e}")

try:
    from buscar import executar_analise
    BUSCAR_AVAILABLE = True
    print("✅ buscar.py carregado com sucesso")
except ImportError as e:
    print(f"❌ Dependências faltando para buscar.py: {e}")
except Exception as e:
    print(f"❌ Erro ao carregar buscar.py: {e}")

# ========== ROTAS ==========
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analises")
def listar_analises():
    if not MODELS_AVAILABLE:
        return render_template("listar_analises.html", analises=[])
    try:
        analises = AnalisePessoaDB.query.order_by(AnalisePessoaDB.data_analise.desc()).all()
        return render_template("listar_analises.html", analises=analises)
    except Exception as e:
        print(f"❌ Erro ao listar análises: {e}")
        return render_template("listar_analises.html", analises=[])

@app.route("/analises/<int:analise_id>")
def detalhar_analise(analise_id):
    if not MODELS_AVAILABLE:
        return render_template("detalhes.html", analise=None)
    
    try:
        analise = AnalisePessoaDB.query.get(analise_id)
        if not analise:
            return render_template("detalhes.html", analise=None)
        
        # Buscar polêmicas e empresas relacionadas
        polemicas = PolemicaDB.query.filter_by(analise_pessoa_id=analise_id).all()
        empresas = EmpresaAssociadaDB.query.filter_by(analise_pessoa_id=analise_id).all()
        
        # Processar fontes consultadas
        fontes_consultadas = []
        if analise.fontes_consultadas:
            try:
                fontes_consultadas = json.loads(analise.fontes_consultadas)
            except:
                fontes_consultadas = []
        
        # Processar tweets relevantes
        tweets_relevantes = []
        if analise.tweets_relevantes:
            try:
                tweets_relevantes = json.loads(analise.tweets_relevantes)
            except:
                tweets_relevantes = []
        
        # Montar dicionário da análise com todos os campos
        analise_dict = {
            'id': analise.id,
            'nome': analise.nome,
            'cargo': analise.cargo,
            'data_analise': analise.data_analise,
            'resumo_analise': analise.resumo_analise or '',
            'risco_reputacao': analise.risco_reputacao or 'desconhecido',
            'recomendacoes': analise.recomendacoes,
            'total_polemicas': analise.total_polemicas if hasattr(analise, 'total_polemicas') else len(polemicas),
            'fontes_consultadas': fontes_consultadas,
            'tweets_relevantes': tweets_relevantes,
            'polemicas': [],
            'empresas_associadas': []
        }
        
        # Processar polêmicas com todos os campos possíveis
        for p in polemicas:
            polemica_dict = {
                'titulo': p.titulo or 'Sem título',
                'descricao': p.descricao or 'Sem descrição',
                'gravidade': p.gravidade or 'media',
                'categoria': p.categoria,
                'fonte_url': p.fonte_url,
                'fonte': p.fonte_url if p.fonte_url else None,
                'impacto_publico': getattr(p, 'impacto_publico', None),
                'impacto': getattr(p, 'impacto', None),
                'data_publicacao': getattr(p, 'data_publicacao', None),
                'evidencias': []
            }
            
            # Tentar extrair evidências se existirem
            if hasattr(p, 'evidencias') and p.evidencias:
                try:
                    polemica_dict['evidencias'] = json.loads(p.evidencias) if isinstance(p.evidencias, str) else p.evidencias
                except:
                    polemica_dict['evidencias'] = []
            
            analise_dict['polemicas'].append(polemica_dict)
        
        # Processar empresas associadas
        for e in empresas:
            empresa_dict = {
                'nome_empresa': e.nome_empresa,
                'cnpj': e.cnpj,
                'relacao': e.relacao,
                'fonte_url': e.fonte_url
            }
            analise_dict['empresas_associadas'].append(empresa_dict)
        
        return render_template("detalhes.html", analise=analise_dict)
        
    except Exception as e:
        print(f"❌ Erro ao detalhar análise {analise_id}: {e}")
        import traceback
        traceback.print_exc()
        return render_template("detalhes.html", analise=None)

@app.route("/api/analises", methods=["POST"])
def criar_analise():
    data = request.get_json(force=True, silent=True)
    
    if not data or "nome" not in data:
        return jsonify({"error": "Campo 'nome' é obrigatório"}), 400
    
    if not BUSCAR_AVAILABLE:
        return jsonify({"error": "Sistema de busca indisponível"}), 500
    
    nome = data.get("nome")
    cargo = data.get("cargo", "")
    
    try:
        resultado = executar_analise(nome, cargo)
        print(f"✅ Busca executada para: {nome}")
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    if not resultado:
        return jsonify({"error": "Análise retornou vazio"}), 500
    
    analise_id = None
    if MODELS_AVAILABLE:
        try:
            nova_analise = AnalisePessoaDB(
                nome=resultado.get('nome', nome),
                cargo=cargo,
                data_analise=datetime.now(),
                fontes_consultadas=json.dumps(resultado.get('fontes_consultadas', []), ensure_ascii=False),
                resumo_analise=resultado.get('resumo_analise', ''),
                risco_reputacao=resultado.get('risco_reputacao', 'desconhecido'),
                recomendacoes=resultado.get('recomendacoes', ''),
                tweets_relevantes=json.dumps(resultado.get('tweets_relevantes', []), ensure_ascii=False),
                total_polemicas=len(resultado.get('polemicas', []))
            )
            db.session.add(nova_analise)
            db.session.flush()
            analise_id = nova_analise.id
            
            for polemica_data in resultado.get('polemicas', []):
                polemica = PolemicaDB(
                    analise_pessoa_id=analise_id,
                    titulo=polemica_data.get('titulo', '')[:255],
                    descricao=polemica_data.get('descricao', ''),
                    gravidade=polemica_data.get('gravidade', 'media'),
                    categoria=polemica_data.get('categoria', 'Outros'),
                    fonte_url=polemica_data.get('fonte_url') or polemica_data.get('fonte', '')
                )
                db.session.add(polemica)
            
            for empresa_data in resultado.get('empresas_associadas', []):
                empresa = EmpresaAssociadaDB(
                    analise_pessoa_id=analise_id,
                    nome_empresa=empresa_data.get('nome_empresa', ''),
                    cnpj=empresa_data.get('cnpj', ''),
                    relacao=empresa_data.get('relacao', ''),
                    fonte_url=empresa_data.get('fonte_url', '')
                )
                db.session.add(empresa)
            
            db.session.commit()
            print(f"✅ Análise salva com ID: {analise_id}")
            return jsonify({"status": "ok", "id": analise_id, "analise": resultado}), 201
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "ok", "id": None, "error": str(e), "analise": resultado}), 201
    
    return jsonify({"status": "ok", "id": None, "analise": resultado}), 201

# ========== INICIALIZAÇÃO ==========
def init_database():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tabelas do banco verificadas/criadas")
        except Exception as e:
            print(f"❌ Erro ao inicializar banco: {e}")

if __name__ == "__main__":
    init_database()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)