import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def analisar_com_gemini(nome_pessoa, resultados_ddgs):
    """Usa o Gemini para analisar os resultados do DuckDuckGo com JSON structured output"""
    
    try:
        # Criar payload otimizado
        resultados_otimizados = []
        for resultado in resultados_ddgs:
            resultados_otimizados.append({
                "t": resultado.get('title', 'N/A'),  # title
                "b": resultado.get('body', 'N/A')    # body
            })

        contexto_compacto = json.dumps({
            "n": nome_pessoa,  # nome
            "r": resultados_otimizados  # resultados
        }, ensure_ascii=False)

        # Configurar o modelo Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Definir o schema para structured output
        schema = {
            "type": "object",
            "properties": {
                "resumo_analise": {"type": "string"},
                "polemicas": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "titulo": {"type": "string"},
                            "descricao": {"type": "string"},
                            "gravidade": {"type": "string", "enum": ["baixa", "media", "alta", "critica"]},
                            "categoria": {"type": "string"},
                            "fonte_url": {"type": "string"}
                        },
                        "required": ["titulo", "descricao", "gravidade", "categoria"]
                    }
                },
                "empresas_associadas": {
                    "type": "array", 
                    "items": {
                        "type": "object",
                        "properties": {
                            "nome_empresa": {"type": "string"},
                            "cnpj": {"type": "string"},
                            "relacao": {"type": "string"},
                            "fonte_url": {"type": "string"}
                        },
                        "required": ["nome_empresa", "relacao"]
                    }
                },
                "risco_reputacao": {"type": "string", "enum": ["BAIXO", "MÉDIO", "ALTO", "CRÍTICO"]},
                "recomendacoes": {"type": "string"},
                "tweets_relevantes": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "fontes_consultadas": {
                    "type": "array", 
                    "items": {"type": "string"}
                }
            },
            "required": ["resumo_analise", "polemicas", "risco_reputacao"]
        }

        prompt = f"""
        ANALISE DE REPUTAÇÃO PÚBLICA - {nome_pessoa.upper()}

        DADOS DA BUSCA (t=title, b=body):
        {contexto_compacto}

        **INSTRUÇÕES CRÍTICAS - SEJA MUITO SELETIVO:**

        🎯 CRITÉRIOS PARA POLÊMICAS (APENAS INCLUA SE ATENDER):
        - EVIDÊNCIAS CONCRETAS de irregularidades, crimes, ou comportamentos éticos questionáveis
        - IMPACTO REAL na reputação pública
        - FONTES CONFIÁVEIS (evite blogs, fóruns sem credibilidade)
        - GRAVIDADE MÍNIMA: apenas inclua se for pelo menos "media"

        ❌ NÃO INCLUA COMO POLÊMICA:
        - Notícias neutras ou positivas sobre a pessoa
        - Menções comuns em notícias sem acusações
        - Conteúdo irrelevante ou duvidoso
        - Informações sem evidências concretas

        📊 CLASSIFICAÇÃO DE RISCO (USE APENAS UMA):
        - "BAIXO": sem polêmicas significativas OU reputação predominantemente positiva
        - "MÉDIO": 1-2 questões menores comprovadas
        - "ALTO": múltiplas questões graves OU um caso sério com evidências
        - "CRÍTICO": crimes graves, corrupção, prisão, organização criminosa

        🔍 FILTRAGEM DE POLÊMICAS:
        - Analise CRITICAMENTE cada resultado
        - Descarte informações duvidosas ou sem fontes confiáveis
        - Priorize evidências de sites oficiais, notícias reputáveis
        - Inclua APENAS polêmicas com EVIDÊNCIAS CONCRETAS

        📝 FORMATO ESPERADO:
        - Seja EXTREMAMENTE seletivo nas polêmicas
        - Inclua APENAS o que for relevante e comprovado
        - Se não houver polêmicas reais, retorne array vazio
        - Risco_reputacao deve refletir APENAS as polêmicas válidas

        **SE NÃO HOUVER EVIDÊNCIAS DE POLÊMICAS REAIS, RETORNE:**
        - "polemicas": [] (array vazio)
        - "risco_reputacao": "BAIXO"
        - "resumo_analise": explicando a ausência de polêmicas significativas

        **SE HOUVER POLÊMICAS, SEJA MUITO ESPECÍFICO E BASEADO EM EVIDÊNCIAS**
        """

        # Fazer a chamada com structured output
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                response_schema=schema
            )
        )
        
        # Parsear a resposta JSON
        resultado_json = json.loads(response.text)
        
        # PÓS-PROCESSAMENTO: Validar e limpar os resultados
        resultado_json = _validar_resultado_gemini(resultado_json)
        
        return resultado_json
        
    except Exception as e:
        print(f"❌ Erro na análise Gemini: {e}")
        return {"error": str(e)}

def _validar_resultado_gemini(resultado):
    """Valida e limpa o resultado do Gemini para garantir qualidade"""
    
    # Garantir campos obrigatórios
    resultado.setdefault('polemicas', [])
    resultado.setdefault('empresas_associadas', [])
    resultado.setdefault('tweets_relevantes', [])
    resultado.setdefault('fontes_consultadas', ['Gemini (Busca Consolidada)'])
    resultado.setdefault('recomendacoes', '')
    
    # Validar risco_reputacao
    risco = resultado.get('risco_reputacao', 'BAIXO').upper().strip()
    if risco not in ["BAIXO", "MÉDIO", "ALTO", "CRÍTICO"]:
        # Recalcular baseado nas polêmicas reais
        if not resultado['polemicas']:
            resultado['risco_reputacao'] = "BAIXO"
        else:
            gravidades = [p.get('gravidade', 'baixa') for p in resultado['polemicas']]
            if any(g == 'critica' for g in gravidades):
                resultado['risco_reputacao'] = "CRÍTICO"
            elif any(g == 'alta' for g in gravidades):
                resultado['risco_reputacao'] = "ALTO"
            elif any(g == 'media' for g in gravidades):
                resultado['risco_reputacao'] = "MÉDIO"
            else:
                resultado['risco_reputacao'] = "BAIXO"
    
    # Filtrar polêmicas de baixa qualidade
    polemicas_filtradas = []
    for polemica in resultado['polemicas']:
        # Verificar se a polêmica tem informações mínimas
        if (polemica.get('titulo') and polemica.get('descricao') and 
            len(polemica['titulo']) > 10 and len(polemica['descricao']) > 20):
            polemicas_filtradas.append(polemica)
    
    resultado['polemicas'] = polemicas_filtradas
    
    # Ajustar resumo se não há polêmicas
    if not resultado['polemicas'] and 'nenhuma polêmica' not in resultado.get('resumo_analise', '').lower():
        resultado['resumo_analise'] = f"Nenhuma polêmica significativa encontrada para {resultado.get('nome', 'a pessoa')} nas fontes consultadas."
    
    return resultado