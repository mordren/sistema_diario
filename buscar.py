import os
import json
from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from ddgs import DDGS
import pandas as pd
import time
from buscador_duck import buscar_dados_duckduckgo_completo
from models import AnalisePessoa, GravidadeEnum, Polemica, TipoFonteEnum
from script_grok import analisar_com_grok
from schemas import AnalisePessoaSchema, PolemicaSchema


# Configuração da API do Grok
XAI_API_KEY = os.environ.get("XAI_API_KEY")

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
    

    def validar_dados_analise(data):
        """Valida dados de entrada para análise"""
        if not data.get('nome') or len(data['nome'].strip()) < 2:
            return False, "Nome inválido"
        if len(data.get('nome', '')) > 200:
            return False, "Nome muito longo"
        return True, ""

    def analisar_pessoa(self, nome_pessoa, cargo_publico=None, estado="Paraná"):
        """Fluxo unificado com buscas melhoradas"""
        print(f"\n🎯 INICIANDO ANÁLISE: {nome_pessoa}")
        if cargo_publico:
            print(f"🏛️  Contexto: {cargo_publico}")
        print("=" * 60)
        
        print("\n🔍 FASE 1: BUSCA INTELIGENTE DUCKDUCKGO...")
        resultados_ddgs = buscar_dados_duckduckgo_completo(nome_pessoa, cargo_publico, estado)
        
        if not resultados_ddgs:
            print("❌ Nenhum resultado relevante encontrado")
            return self._criar_analise_vazia(nome_pessoa, cargo_publico)
        
        print(f"✅ Encontrados {len(resultados_ddgs)} resultados relevantes")
        self._salvar_resultados_brutos(resultados_ddgs, nome_pessoa)

        print("\n🤖 FASE 2: ANÁLISE COM GROK...")
        analise_grok = analisar_com_grok(nome_pessoa, resultados_ddgs)
        
        # Fase 3: Consolidação final
        print("\n📊 FASE 3: CONSOLIDAÇÃO DOS RESULTADOS...")
        analise_final = self._processar_analise_final(analise_grok, resultados_ddgs, nome_pessoa, cargo_publico)
        
        print("\n💾 FASE 4: SALVANDO RESULTADOS...")
        self._salvar_analise_completa(analise_final, nome_pessoa)
        
        return analise_final
    
    def _processar_analise_final(self, analise_grok, resultados_ddgs, nome_pessoa, cargo_publico):
        """Processa e consolida a análise final com lógica melhorada"""

        if not analise_grok or "error" in analise_grok:
            print("⚠️ Usando fallback DuckDuckGo (Grok indisponível)")
            return self._criar_analise_ddgs(resultados_ddgs, nome_pessoa, cargo_publico)
        
        if not isinstance(analise_grok, dict):
            print("⚠️ Resposta do Grok inválida, usando fallback")
            return self._criar_analise_ddgs(resultados_ddgs, nome_pessoa, cargo_publico)
        
        if 'fontes_consultadas' not in analise_grok:
            analise_grok['fontes_consultadas'] = []
        
        if 'tweets_relevantes' not in analise_grok:
            analise_grok['tweets_relevantes'] = []
        
        if 'polemicas' not in analise_grok:
            analise_grok['polemicas'] = []
        
        # Adicionar fonte DuckDuckGo
        if "DuckDuckGo (Busca Consolidada)" not in analise_grok['fontes_consultadas']:
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
        
        if tweets and not analise_grok['tweets_relevantes']:
            analise_grok['tweets_relevantes'] = tweets
        
        # ANÁLISE DE CONTEXTO MELHORADA
        texto_completo = " ".join([
            str(resultado.get('title', '')) + " " + str(resultado.get('body', '')) 
            for resultado in resultados_ddgs
        ]).lower()
        
        # Verificar se há predominantemente conteúdo positivo
        termos_positivos_contexto = [
            'positivo', 'favorável', 'elogio', 'reconhecimento', 'competente',
            'eficiente', 'confiança', 'honesto', 'íntegro', 'trabalho'
        ]
        
        termos_negativos_contexto = [
            'corrupção', 'fraude', 'crime', 'condenado', 'prisão',
            'irregularidade', 'denúncia', 'processo', 'investigação'
        ]
        
        count_positivo = sum(1 for termo in termos_positivos_contexto if termo in texto_completo)
        count_negativo = sum(1 for termo in termos_negativos_contexto if termo in texto_completo)
        
        # Se contexto é predominantemente positivo, ajustar risco
        if count_positivo > count_negativo * 2:  # Muito mais positivo que negativo
            risco_ajustado = "BAIXO"
        elif count_positivo > count_negativo:    # Mais positivo que negativo
            risco_ajustado = "BAIXO"
        else:
            risco_ajustado = self._calcular_risco_geral(analise_grok.get('polemicas', []))
        
        # Garantir campos essenciais
        if 'data_analise' not in analise_grok:
            analise_grok['data_analise'] = datetime.now().isoformat()
        
        if 'nome' not in analise_grok:
            analise_grok['nome'] = nome_pessoa
        
        if 'cargo_publico' not in analise_grok:
            analise_grok['cargo_publico'] = cargo_publico
        
        if 'total_polemicas' not in analise_grok:
            analise_grok['total_polemicas'] = len(analise_grok.get('polemicas', []))
        
        if 'risco_reputacao' not in analise_grok:
            analise_grok['risco_reputacao'] = risco_ajustado
        
        if 'resumo_analise' not in analise_grok:
            analise_grok['resumo_analise'] = "Análise realizada com sucesso"
        
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
        """Classificação de gravidade MAIS PRECISA"""
        if not texto:
            return "baixa"
            
        texto = texto.lower()
        
        # Termos CRÍTICOS - crimes graves
        termos_criticos = [
            'condenado', 'prisão', 'crime', 'lavagem de dinheiro', 'tráfico',
            'assassinato', 'homicídio', 'pedofilia', 'estupro', 'racismo'
        ]
        
        # Termos ALTOS - corrupção, fraudes graves
        termos_altos = [
            'corrupção', 'desvio', 'propina', 'improbidade', 'fraude',
            'superfaturamento', 'licitação fraudulenta', 'caixa dois',
            'sonegação fiscal', 'lavagem de capitais'
        ]
        
        # Termos MÉDIOS - investigações, processos
        termos_medios = [
            'investigação', 'processo', 'denúncia', 'inquérito', 'apuração',
            'irregularidade', 'tribunal de contas', 'tce', 'mpf', 'pf'
        ]
        
        # Termos BAIXOS - polêmicas leves, críticas
        termos_baixos = [
            'polêmica', 'controvérsia', 'crítica', 'questionamento',
            'acórdão', 'escrutínio', 'auditoria', 'recomendação'
        ]
        
        # Termos POSITIVOS - que devem reduzir gravidade
        termos_positivos = [
            'absolvido', 'inocente', 'arquivado', 'improcedente',
            'favorável', 'positivo', 'elogio', 'reconhecimento'
        ]
        
        # Verificar termos positivos primeiro (reduzem gravidade)
        if any(termo in texto for termo in termos_positivos):
            return "baixa"
        
        # Classificar por gravidade
        if any(termo in texto for termo in termos_criticos):
            return "critica"
        elif any(termo in texto for termo in termos_altos):
            return "alta"
        elif any(termo in texto for termo in termos_medios):
            return "media"
        elif any(termo in texto for termo in termos_baixos):
            return "baixa"
        else:
            return "baixa"  # Padrão conservador: quando não sabe, classifica como baixo
    
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
        """Calcula o risco geral baseado nas polêmicas encontradas"""
        if not polemicas:
            return "BAIXO"  # Sem polêmicas = risco baixo
        
        # Contar gravidades
        gravidades = [p.get('gravidade', 'baixa').lower() for p in polemicas]
        
        critica_count = gravidades.count('critica')
        alta_count = gravidades.count('alta') 
        media_count = gravidades.count('media')
        baixa_count = gravidades.count('baixa')
        
        # Lógica de classificação MELHORADA
        if critica_count > 0:
            return "CRÍTICA"
        elif alta_count >= 2 or (alta_count >= 1 and media_count >= 2):
            return "ALTA"
        elif alta_count >= 1 or media_count >= 2:
            return "MÉDIA"
        elif media_count >= 1:
            return "BAIXA"  # Polêmicas leves = risco baixo
        else:
            return "BAIXO"  # Apenas polêmicas baixas = risco baixo
    
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
        print(f"\n📊 RELATÓRIO FINAL - {analise.get('nome', 'N/A')}")
        print("=" * 50)
        print(f"🔍 Polêmicas encontradas: {analise.get('total_polemicas', 0)}")
        print(f"🚨 Risco reputação: {str(analise.get('risco_reputacao', 'N/A')).upper()}")
        print(f"📅 Data análise: {analise.get('data_analise', '')[:10]}")
        print(f"🔧 Fontes: {', '.join(analise.get('fontes_consultadas', []))}")
        
        if analise.get('tweets_relevantes'):
            print(f"🦅 Tweets relevantes: {len(analise['tweets_relevantes'])}")
        
        if analise.get('polemicas'):
            print(f"\n🎯 PRINCIPAIS POLÊMICAS:")
            for i, polemica in enumerate(analise['polemicas'][:3], 1):
                print(f"\n{i}. {polemica.get('titulo', 'N/A')}")
                print(f"   📊 Gravidade: {str(polemica.get('gravidade', 'N/A')).upper()}")
                descricao = polemica.get('descricao', 'N/A')
                print(f"   📝 {descricao[:100]}...")
                print(f"   🔗 Fonte: {polemica.get('tipo_fonte', 'N/A')}")

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
        import traceback
        traceback.print_exc()
        return None

# EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    nome = "SANDRO ALEX CRUZ DE OLIVEIRA"  # 🔧 ALTERE AQUI
    cargo = "Trabalha no governo estadual do paraná"  # 🔧 OPCIONAL
    
    resultado = executar_analise(nome, cargo)