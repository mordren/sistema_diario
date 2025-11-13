import os
import json
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from ddgs import DDGS
import pandas as pd
import time

# Configuração da API do Grok
XAI_API_KEY = os.environ.get("XAI_API_KEY")

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

class Polemica(BaseModel):
    titulo: str = Field(description="Título resumido da polêmica")
    descricao: str = Field(description="Descrição detalhada da polêmica")
    fonte: str = Field(description="URL ou origem da informação")
    tipo_fonte: TipoFonteEnum = Field(description="Tipo da fonte da informação")
    data_incidente: Optional[str] = Field(description="Data do incidente se disponível")
    gravidade: GravidadeEnum = Field(description="Nível de gravidade da polêmica")
    categorias: List[str] = Field(description="Categorias da polêmica")
    evidencias: List[str] = Field(description="Evidências ou provas mencionadas")
    impacto_publico: str = Field(description="Potencial impacto na opinião pública")
    relevancia: str = Field(description="Relevância da informação encontrada")

class AnalisePessoa(BaseModel):
    nome: str = Field(description="Nome completo da pessoa analisada")
    cargo_publico: Optional[str] = Field(description="Cargo público se aplicável")
    total_polemicas: int = Field(description="Número total de polêmicas encontradas")
    polemicas: List[Polemica] = Field(description="Lista de polêmicas identificadas")
    resumo_analise: str = Field(description="Resumo geral da análise")
    risco_reputacao: GravidadeEnum = Field(description="Risco geral para reputação")
    data_analise: str = Field(description="Data da análise")
    fontes_consultadas: List[str] = Field(description="Fontes utilizadas na pesquisa")
    tweets_relevantes: List[str] = Field(description="Tweets relevantes encontrados")

class BuscadorTwitterUnificado:
    def __init__(self):
        self.ddgs = DDGS()
        try:
            from xai_sdk import Client
            self.client = Client(api_key=XAI_API_KEY)
            self.grok_available = True
        except ImportError:
            print("⚠️ SDK do Grok não disponível")
            self.grok_available = False
    
    def buscar_dados_duckduckgo_completo(self, nome_pessoa):
        """Busca abrangente no DuckDuckGo com múltiplas queries"""
        print(f"🔍 Buscando dados para: {nome_pessoa}")
        
        queries = [
            f'"{nome_pessoa}" twitter polêmica',
            f'"{nome_pessoa}" escândalo',
            f'"{nome_pessoa}" processo judicial',
            f'"{nome_pessoa}" licitação irregular',
            f'"{nome_pessoa}" MPF investigação',
            f'"{nome_pessoa}" condenado',
            f'"{nome_pessoa}" fraude',
            f'"{nome_pessoa}" corrupção',
            f'"{nome_pessoa}" improbidade',
            f'"{nome_pessoa}" desvio de verba'
        ]
        
        todos_resultados = []
        
        for i, query in enumerate(queries, 1):
            print(f"  📝 Query {i}/10: {query}")
            try:
                results = list(self.ddgs.text(
                    query=query,
                    region='br-pt',
                    max_results=8
                ))
                todos_resultados.extend(results)
                print(f"    ✅ Encontrados: {len(results)} resultados")
                time.sleep(1.5)  # Rate limiting
            except Exception as e:
                print(f"    ❌ Erro na query '{query}': {e}")
                continue
        
        # Remover duplicatas
        resultados_unicos = []
        urls_vistas = set()
        
        for resultado in todos_resultados:
            url = resultado.get('href', '')
            if url and url not in urls_vistas:
                urls_vistas.add(url)
                resultados_unicos.append(resultado)
        
        print(f"🎯 Total de resultados únicos: {len(resultados_unicos)}")
        return resultados_unicos
    
    def analisar_com_grok(self, nome_pessoa, resultados_ddgs):
        """Usa o Grok para analisar os resultados do DuckDuckGo"""
        if not self.grok_available:
            return {"error": "Grok não disponível"}
        
        try:
            from xai_sdk.chat import system, user
            
            # Preparar contexto consolidado
            contexto_ddgs = "RESULTADOS CONSOLIDADOS DO DUCKDUCKGO:\n\n"
            for i, resultado in enumerate(resultados_ddgs, 1):
                contexto_ddgs += f"--- RESULTADO {i} ---\n"
                contexto_ddgs += f"Título: {resultado.get('title', 'N/A')}\n"
                contexto_ddgs += f"URL: {resultado.get('href', 'N/A')}\n"
                contexto_ddgs += f"Descrição: {resultado.get('body', 'N/A')}\n"
                contexto_ddgs += f"Fonte: {self._classificar_fonte_simples(resultado.get('href', ''))}\n\n"
            
            chat = self.client.chat.create(model="grok-2-1212")
            
            prompt = f"""
            ANALISE DE REPUTAÇÃO PÚBLICA - {nome_pessoa.upper()}

            BASEADO NOS SEGUINTES RESULTADOS CONSOLIDADOS DE BUSCA:
            {contexto_ddgs}

            ANALISE ESTES RESULTADOS E IDENTIFIQUE:

            🔍 POLÊMICAS E CONTROVÉRSIAS:
            - Listar cada polêmica encontrada com título descritivo
            - Incluir URL da fonte
            - Classificar gravidade (baixa, media, alta, critica)
            - Categorizar (Licitações, Judicial, Eleitoral, etc)

            📊 ANÁLISE DE RISCO:
            - Risco geral para reputação
            - Padrões de comportamento problemático
            - Impacto potencial na opinião pública

            🎯 DIRETRIZES:
            - Seja objetivo e factual
            - Baseie-se apenas nas informações fornecidas
            - Priorize fontes confiáveis (sites oficiais, notícias)
            - Inclua tweets apenas quando relevantes como evidência
            """
            
            chat.append(system("Você é um analista especializado em due diligence e análise de reputação pública com expertise jurídica e política."))
            chat.append(user(prompt))
            
            response, analise = chat.parse(AnalisePessoa)
            
            return analise.dict()
            
        except Exception as e:
            print(f"❌ Erro na análise Grok: {e}")
            return {"error": str(e)}
    
    def _classificar_fonte_simples(self, url):
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

class AnalisadorUnificado:
    def __init__(self):
        self.buscador = BuscadorTwitterUnificado()
    
    def analisar_pessoa(self, nome_pessoa, cargo_publico=None):
        """Fluxo unificado: DuckDuckGo -> Grok -> Análise"""
        print(f"\n🎯 INICIANDO ANÁLISE: {nome_pessoa}")
        print("=" * 60)
        
        # Fase 1: Busca consolidada no DuckDuckGo
        print("\n🔍 FASE 1: BUSCA CONSOLIDADA DUCKDUCKGO...")
        resultados_ddgs = self.buscador.buscar_dados_duckduckgo_completo(nome_pessoa)
        
        if not resultados_ddgs:
            print("❌ Nenhum resultado encontrado no DuckDuckGo")
            return self._criar_analise_vazia(nome_pessoa, cargo_publico)
        
        # Salvar resultados brutos
        self._salvar_resultados_brutos(resultados_ddgs, nome_pessoa)
        
        # Fase 2: Análise com Grok
        print("\n🤖 FASE 2: ANÁLISE COM GROK...")
        analise_grok = self.buscador.analisar_com_grok(nome_pessoa, resultados_ddgs)
        
        # Fase 3: Consolidação final
        print("\n📊 FASE 3: CONSOLIDAÇÃO DOS RESULTADOS...")
        analise_final = self._processar_analise_final(analise_grok, resultados_ddgs, nome_pessoa, cargo_publico)
        
        # Fase 4: Salvar e reportar
        print("\n💾 FASE 4: SALVANDO RESULTADOS...")
        self._salvar_analise_completa(analise_final, nome_pessoa)
        
        return analise_final
    
    def _processar_analise_final(self, analise_grok, resultados_ddgs, nome_pessoa, cargo_publico):
        """Processa e consolida a análise final"""
        
        # Se Grok falhou, criar análise básica com DuckDuckGo
        if "error" in analise_grok:
            print("⚠️ Usando fallback DuckDuckGo (Grok indisponível)")
            return self._criar_analise_ddgs(resultados_ddgs, nome_pessoa, cargo_publico)
        
        # Enriquecer análise do Grok com dados do DuckDuckGo
        analise_grok['fontes_consultadas'].append("DuckDuckGo (Busca Consolidada)")
        
        # Extrair tweets relevantes dos resultados
        tweets = []
        for resultado in resultados_ddgs:
            url = resultado.get('href', '')
            if 'twitter.com' in url or 'x.com' in url:
                tweet_info = {
                    'texto': resultado.get('title', ''),
                    'url': url,
                    'descricao': resultado.get('body', '')[:150]
                }
                tweets.append(json.dumps(tweet_info, ensure_ascii=False))
        
        if tweets:
            analise_grok['tweets_relevantes'] = tweets
        
        analise_grok['data_analise'] = datetime.now().isoformat()
        
        return analise_grok
    
    def _criar_analise_ddgs(self, resultados_ddgs, nome_pessoa, cargo_publico):
        """Cria análise baseada apenas no DuckDuckGo"""
        polemicas = []
        
        for resultado in resultados_ddgs:
            polemica = Polemica(
                titulo=resultado.get('title', 'Sem título')[:100],
                descricao=resultado.get('body', 'Sem descrição')[:200],
                fonte=resultado.get('href', ''),
                tipo_fonte=self._classificar_fonte(resultado.get('href', '')),
                gravidade=self._classificar_gravidade(resultado.get('title', '') + resultado.get('body', '')),
                categorias=self._extrair_categorias(resultado.get('title', '') + resultado.get('body', '')),
                evidencias=[resultado.get('body', '')[:100]],
                impacto_publico="A ser avaliado",
                relevancia="Média"
            )
            polemicas.append(polemica.dict())
        
        analise = AnalisePessoa(
            nome=nome_pessoa,
            cargo_publico=cargo_publico,
            total_polemicas=len(polemicas),
            polemicas=polemicas,
            resumo_analise="Análise baseada em busca DuckDuckGo - Grok indisponível",
            risco_reputacao=self._calcular_risco_geral(polemicas),
            data_analise=datetime.now().isoformat(),
            fontes_consultadas=["DuckDuckGo (Busca Consolidada)"],
            tweets_relevantes=[]
        )
        
        return analise.dict()
    
    def _criar_analise_vazia(self, nome_pessoa, cargo_publico):
        """Cria análise vazia quando não há resultados"""
        analise = AnalisePessoa(
            nome=nome_pessoa,
            cargo_publico=cargo_publico,
            total_polemicas=0,
            polemicas=[],
            resumo_analise="Nenhuma polêmica encontrada nas buscas realizadas",
            risco_reputacao=GravidadeEnum.BAIXA,
            data_analise=datetime.now().isoformat(),
            fontes_consultadas=["DuckDuckGo"],
            tweets_relevantes=[]
        )
        return analise.dict()
    
    def _classificar_fonte(self, url):
        url = url.lower()
        if 'twitter.com' in url or 'x.com' in url:
            return TipoFonteEnum.TWITTER
        elif any(site in url for site in ['.gov', '.jus', '.mp']):
            return TipoFonteEnum.SITE_OFICIAL
        elif any(site in url for site in ['.com.br', '.com']):
            return TipoFonteEnum.NOTICIA
        else:
            return TipoFonteEnum.BLOG
    
    def _classificar_gravidade(self, texto):
        texto = texto.lower()
        if any(termo in texto for termo in ['corrupção', 'condenado', 'prisão', 'desvio', 'crime']):
            return GravidadeEnum.CRITICA
        elif any(termo in texto for termo in ['investigação', 'processo', 'denúncia', 'improbidade', 'fraude']):
            return GravidadeEnum.ALTA
        elif any(termo in texto for termo in ['polêmica', 'controvérsia', 'crítica', 'questionamento']):
            return GravidadeEnum.MEDIA
        else:
            return GravidadeEnum.BAIXA
    
    def _extrair_categorias(self, texto):
        categorias = []
        texto = texto.lower()
        
        if any(termo in texto for termo in ['licitação', 'contrato', 'pregão']):
            categorias.append("Licitações")
        if any(termo in texto for termo in ['eleição', 'campanha', 'doação']):
            categorias.append("Eleitoral")
        if any(termo in texto for termo in ['corrupção', 'desvio', 'propina']):
            categorias.append("Corrupção")
        if any(termo in texto for termo in ['processo', 'judicial', 'tribunal']):
            categorias.append("Judicial")
            
        return categorias if categorias else ["Outros"]
    
    def _calcular_risco_geral(self, polemicas):
        if not polemicas:
            return GravidadeEnum.BAIXA
        
        gravidades = [p.get('gravidade', 'baixa') for p in polemicas]
        if any(g == 'critica' for g in gravidades):
            return GravidadeEnum.CRITICA
        elif any(g == 'alta' for g in gravidades):
            return GravidadeEnum.ALTA
        elif any(g == 'media' for g in gravidades):
            return GravidadeEnum.MEDIA
        else:
            return GravidadeEnum.BAIXA
    
    def _salvar_resultados_brutos(self, resultados_ddgs, nome_pessoa):
        """Salva resultados brutos do DuckDuckGo"""
        arquivo_bruto = f"resultados_brutos_{nome_pessoa.replace(' ', '_')}.json"
        dados_brutos = {
            'nome_pessoa': nome_pessoa,
            'data_busca': datetime.now().isoformat(),
            'total_resultados': len(resultados_ddgs),
            'resultados': resultados_ddgs
        }
        
        with open(arquivo_bruto, 'w', encoding='utf-8') as f:
            json.dump(dados_brutos, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Dados brutos salvos: {arquivo_bruto}")
    
    def _salvar_analise_completa(self, analise, nome_pessoa):
        """Salva análise completa em JSON"""
        arquivo = f"analise_completa_{nome_pessoa.replace(' ', '_')}.json"
        
        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(analise, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Análise salva: {arquivo}")
        
        # Gerar relatório resumido
        self._gerar_relatorio_console(analise)
    
    def _gerar_relatorio_console(self, analise):
        """Gera relatório resumido no console"""
        print(f"\n📊 RELATÓRIO FINAL - {analise['nome']}")
        print("=" * 50)
        print(f"🔍 Polêmicas encontradas: {analise['total_polemicas']}")
        print(f"🚨 Risco reputação: {analise['risco_reputacao'].upper()}")
        print(f"📅 Data análise: {analise['data_analise'][:10]}")
        print(f"🔧 Fontes: {', '.join(analise['fontes_consultadas'])}")
        
        if analise.get('tweets_relevantes'):
            print(f"🐦 Tweets relevantes: {len(analise['tweets_relevantes'])}")
        
        if analise['polemicas']:
            print(f"\n🎯 PRINCIPAIS POLÊMICAS:")
            for i, polemica in enumerate(analise['polemicas'][:3], 1):
                print(f"\n{i}. {polemica['titulo']}")
                print(f"   📍 Gravidade: {polemica['gravidade'].upper()}")
                print(f"   📝 {polemica['descricao'][:100]}...")
                print(f"   🔗 Fonte: {polemica['tipo_fonte']}")

def executar_analise(nome_pessoa, cargo=None):
    """Função principal para executar análise"""
    analisador = AnalisadorUnificado()
    
    print(f"\n{'#'*60}")
    print(f"🚀 INICIANDO ANÁLISE UNIFICADA: {nome_pessoa}")
    print(f"{'#'*60}")
    
    try:
        inicio = time.time()
        analise = analisador.analisar_pessoa(nome_pessoa, cargo)
        tempo_total = time.time() - inicio
        
        print(f"\n✅ ANÁLISE CONCLUÍDA em {tempo_total:.1f} segundos")
        return analise
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return None

# EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    nome = "SANDRO ALEX CRUZ DE OLIVEIRA"  # 🔧 ALTERE AQUI
    cargo = "Trabalha no governo estadual do paraná"  # 🔧 OPCIONAL
    
    resultado = executar_analise(nome, cargo)