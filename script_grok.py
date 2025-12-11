import json
import os
from dotenv import load_dotenv
from xai_sdk.chat import system, user
from models import AnalisePessoa
from xai_sdk import Client


load_dotenv()

XAI_API_KEY = os.environ.get("XAI_API_KEY")
client = Client(api_key=XAI_API_KEY)

def _classificar_fonte_simples(url):
    """Classificação simples da fonte para contexto"""
    url = url.lower()
    if 'twitter.com' in url or 'x.com' in url:
        return "Twitter"
    elif any(site in url for site in ['.gov', '.jus', '.mp', 'tribunal', 'justiça']):
        return "Site Oficial"
    elif any(site in url for site in ['g1', 'uol', 'folha', 'estadao', 'oglobo']):
        return "Notícia"
    else:
        return "Blog/Forum"

def analisar_com_grok(nome_pessoa, resultados_ddgs):
    """Usa o Grok para analisar os resultados do DuckDuckGo"""
    
    try:       
        resultados_otimizados = []
        for resultado in resultados_ddgs:
            resultados_otimizados.append({
                "t": resultado.get('title', 'N/A'),  # title
                "b": resultado.get('body', 'N/A'),    # body
                "h": resultado.get('href', 'N/A')
            })

        contexto_compacto = json.dumps({
            "n": nome_pessoa,  
            "r": resultados_otimizados  
        }, ensure_ascii=False)

        chat = client.chat.create(model="grok-4-fast-reasoning")
        
        prompt = f"""
        ANALISE DE REPUTAÇÃO PÚBLICA - {nome_pessoa.upper()}

        BASEADO NOS SEGUINTES RESULTADOS CONSOLIDADOS DE BUSCA:
        {contexto_compacto}

        **INSTRUÇÕES CRÍTICAS:**
        - Para 'risco_reputacao' use APENAS UMA DESTAS OPÇÕES: "BAIXO", "MÉDIO", "ALTO", "CRÍTICO"
        - Seja CONCISO e OBJETIVO
        - Use classificação padronizada

        **ANALISE ESTES RESULTADOS E IDENTIFIQUE:**

        🔍 POLÊMICAS E CONTROVÉRSIAS:
        - Para CADA polêmica, inclua:
          * titulo: breve e descritivo (máx 100 caracteres)
          * descricao: resumo objetivo (máx 200 caracteres)
          * gravidade: "baixa", "media", "alta" ou "critica"
          * categoria: "Judicial", "Corrupção", "Licitações", "Eleitoral", etc.
          * fonte_url: URL da fonte

        📊 CLASSIFICAÇÃO DE RISCO (USE APENAS UMA DESTAS):
        - "BAIXO": sem polêmicas significativas ou apenas questões menores
        - "MÉDIO": algumas questões problemáticas, mas sem gravidade extrema
        - "ALTO": múltiplas questões graves ou envolvimento em casos sérios
        - "CRÍTICO": envolvimento em crimes graves, corrupção, prisão, etc.

        🎯 DIRETRIZES:
        - Seja objetivo e factual
        - Baseie-se apenas nas informações fornecidas
        - Priorize fontes confiáveis (sites oficiais, notícias)
        - Para risco_reputacao: APENAS UMA PALAVRA das opções acima
        - Resumo deve ter no máximo 2-3 frases
        - Recomendações devem ser práticas e diretas
        - colocar os links completos para acessar 

        Quando possível traga o CNPJ das empresas que estão sendo citadas ai, as que estão relacionadas com a pessoa buscada.

        """

        chat.append(system("""Você é um analista especializado em due diligence e análise de reputação pública. 
        Siga STRITAMENTE estas regras:
        1. Para 'risco_reputacao' use APENAS: "BAIXO", "MÉDIO", "ALTO" ou "CRÍTICO"
        2. Seja conciso e objetivo em todas as respostas
        3. Use classificação padronizada para gravidade das polêmicas
        4. Mantenha títulos e descrições CURTOS
        5. Baseie-se apenas nas evidências fornecidas"""))
        
        chat.append(user(prompt))
        
        response, analise = chat.parse(AnalisePessoa)
        
        # PÓS-PROCESSAMENTO: Garantir que risco_reputacao esteja padronizado
        resultado = analise.dict()
        
        # Normalizar o campo risco_reputacao
        if 'risco_reputacao' in resultado:
            risco = resultado['risco_reputacao'].upper().strip()
            opcoes_validas = ["BAIXO", "MÉDIO", "ALTO", "CRÍTICO"]
            
            # Se não estiver nas opções válidas, tentar extrair
            if risco not in opcoes_validas:
                if any(palavra in risco for palavra in ["CRÍTIC", "CRITIC"]):
                    resultado['risco_reputacao'] = "CRÍTICO"
                elif any(palavra in risco for palavra in ["ALT", "HIGH"]):
                    resultado['risco_reputacao'] = "ALTO"
                elif any(palavra in risco for palavra in ["MÉDI", "MEDI", "MEDIUM"]):
                    resultado['risco_reputacao'] = "MÉDIO"
                elif any(palavra in risco for palavra in ["BAIX", "LOW"]):
                    resultado['risco_reputacao'] = "BAIXO"
                else:
                    # Fallback: calcular baseado nas polêmicas
                    gravidades = [p.get('gravidade', 'baixa') for p in resultado.get('polemicas', [])]
                    if any(g in ['critica'] for g in gravidades):
                        resultado['risco_reputacao'] = "CRÍTICO"
                    elif any(g in ['alta'] for g in gravidades):
                        resultado['risco_reputacao'] = "ALTO"
                    elif any(g in ['media'] for g in gravidades):
                        resultado['risco_reputacao'] = "MÉDIO"
                    else:
                        resultado['risco_reputacao'] = "BAIXO"
        
        return resultado
        
    except Exception as e:
        print(f"❌ Erro na análise Grok: {e}")
        return {"error": str(e)}