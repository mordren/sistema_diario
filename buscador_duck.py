import time
import re
from datetime import datetime, timedelta
from ddgs import DDGS

duck = DDGS()

def buscar_dados_duckduckgo_completo(nome_pessoa, cargo_publico=None, estado=None):
    """Busca INTELIGENTE no DuckDuckGo com queries contextuais"""
    print(f"🔍 Buscando dados para: {nome_pessoa}")
    
    # Extrair contexto do cargo
    contexto = _extrair_contexto_cargo(cargo_publico, estado)
    
    # Queries PRIMÁRIAS (mais específicas)
    queries_primarias = _gerar_queries_primarias(nome_pessoa, contexto)
    
    # Queries SECUNDÁRIAS (backup - mais genéricas)
    queries_secundarias = _gerar_queries_secundarias(nome_pessoa, contexto)
    
    todos_resultados = []
    
    # Buscar PRIMEIRO com queries específicas
    print("🎯 FASE 1: Buscas específicas...")
    for i, query in enumerate(queries_primarias, 1):
        resultados = _executar_query_segura(query, i, len(queries_primarias))
        if resultados:
            todos_resultados.extend(resultados)
    
    # Se poucos resultados, buscar com queries secundárias
    if len(todos_resultados) < 15:
        print("🔄 FASE 2: Buscas complementares...")
        for i, query in enumerate(queries_secundarias, 1):
            resultados = _executar_query_segura(query, i, len(queries_secundarias))
            if resultados:
                todos_resultados.extend(resultados)
    
    # FILTRAGEM INTELIGENTE
    resultados_filtrados = _filtrar_resultados_inteligente(todos_resultados, nome_pessoa)
    
    print(f"🎯 Resultados após filtragem: {len(resultados_filtrados)}")
    return resultados_filtrados

def _extrair_contexto_cargo(cargo_publico, estado):
    """Extrai contexto específico do cargo para refinar buscas"""
    contexto = {}
    
    if cargo_publico:
        cargo_lower = cargo_publico.lower()
        
        # Detectar nível de governo
        if any(termo in cargo_lower for termo in ['federal', 'ministro', 'presidente', 'senador', 'deputado federal']):
            contexto['nivel'] = 'federal'
        elif any(termo in cargo_lower for termo in ['estadual', 'governador', 'deputado estadual', 'secretário estadual']):
            contexto['nivel'] = 'estadual'
            contexto['estado'] = estado
        elif any(termo in cargo_lower for termo in ['municipal', 'prefeito', 'vereador', 'secretário municipal']):
            contexto['nivel'] = 'municipal'
        
        # Detectar área de atuação
        areas = {
            'saúde': ['saúde', 'hospital', 'sus', 'secretário saúde'],
            'educação': ['educação', 'escola', 'universidade', 'secretário educação'],
            'infraestrutura': ['obras', 'infraestrutura', 'construção', 'secretário obras'],
            'segurança': ['segurança', 'polícia', 'secretário segurança'],
            'fazenda': ['fazenda', 'finanças', 'secretário fazenda', 'economia']
        }
        
        for area, termos in areas.items():
            if any(termo in cargo_lower for termo in termos):
                contexto['area'] = area
                break
    
    return contexto

def _gerar_queries_primarias(nome_pessoa, contexto):
    """Gera queries ALTAMENTE específicas baseadas no contexto"""
    queries = []
    
    # Query base com nome exato
    queries.append(f'"{nome_pessoa}"')
    
    # Adicionar contexto de governo se disponível
    if contexto.get('nivel') == 'federal':
        queries.extend([
            f'"{nome_pessoa}" ministério',
            f'"{nome_pessoa}" governo federal',
            f'"{nome_pessoa}" brasília',
        ])
    elif contexto.get('nivel') == 'estadual':
        estado = contexto.get('estado', '')
        queries.extend([
            f'"{nome_pessoa}" {estado}',
            f'"{nome_pessoa}" governo {estado}',
            f'"{nome_pessoa}" secretaria {estado}',
        ])
    
    # Adicionar contexto de área específica
    if contexto.get('area'):
        area = contexto['area']
        queries.extend([
            f'"{nome_pessoa}" {area}',
            f'"{nome_pessoa}" secretário {area}',
        ])
    
    # Queries jurídicas específicas
    queries.extend([
        f'"{nome_pessoa}" processo judicial',
        f'"{nome_pessoa}" ação judicial',
        f'"{nome_pessoa}" tribunal de contas',
        f'"{nome_pessoa}" TCU',
        f'"{nome_pessoa}" MPF',
        f'"{nome_pessoa}" PF',
        f'"{nome_pessoa}" investigação',
    ])
    
    # Queries de licitações/contratos
    queries.extend([
        f'"{nome_pessoa}" licitação',
        f'"{nome_pessoa}" contrato governo',
        f'"{nome_pessoa}" pregão',
        f'"{nome_pessoa}" diário oficial',
    ])
    
    return queries

def _gerar_queries_secundarias(nome_pessoa, contexto):
    """Gera queries mais genéricas como backup"""
    queries = []
    
    # Dividir nome para buscas parciais
    partes_nome = nome_pessoa.split()
    if len(partes_nome) >= 2:
        primeiro_ultimo = f'"{partes_nome[0]} {partes_nome[-1]}"'
        queries.append(primeiro_ultimo)
    
    # Queries genéricas mas relevantes
    termos_relevantes = [
        'polêmica', 'escândalo', 'denúncia', 'corrupção', 'fraude',
        'condenado', 'investigação', 'irregularidade', 'improbidade',
        'desvio', 'superfaturamento', 'lavagem', 'tribunal'
    ]
    
    for termo in termos_relevantes:
        queries.append(f'"{nome_pessoa}" {termo}')
    
    # Adicionar contexto se disponível
    if contexto.get('nivel'):
        nivel = contexto['nivel']
        queries.append(f'"{nome_pessoa}" {nivel}')
    
    return queries

def _executar_query_segura(query, numero_atual, total_queries):
    """Executa query com tratamento de erro e rate limiting inteligente"""
    print(f"  📝 Query {numero_atual}/{total_queries}: {query}")
    
    try:
        results = list(duck.text(
            query=query,
            region='br-pt',
            max_results=10,  # Aumentado para captar mais contexto
            timelimit='y'  # Último ano apenas
        ))
        
        # Filtrar resultados irrelevantes
        results = [r for r in results if _validar_relevancia_resultado(r, query)]
        
        print(f"    ✅ Encontrados: {len(results)} resultados válidos")
        
        # Rate limiting adaptativo
        if len(results) > 5:
            time.sleep(2)  # Mais resultados = mais tempo
        else:
            time.sleep(1)
            
        return results
        
    except Exception as e:
        print(f"    ❌ Erro na query '{query}': {e}")
        time.sleep(3)  # Mais tempo em caso de erro
        return []

def _validar_relevancia_resultado(resultado, query_original):
    """Valida se o resultado é relevante baseado em múltiplos critérios"""
    title = resultado.get('title', '').lower()
    body = resultado.get('body', '').lower()
    href = resultado.get('href', '').lower()
    
    # Critérios de EXCLUSÃO (fontes irrelevantes)
    fontes_irrelevantes = [
        'wikipedia.org', 'instagram.com', 'facebook.com', 'youtube.com',
        'linkedin.com', 'blogspot.com', 'wordpress.com'
    ]
    
    if any(fonte in href for fonte in fontes_irrelevantes):
        return False
    
    # Critérios de QUALIDADE (fontes preferenciais)
    fontes_preferenciais = [
        '.gov', '.jus', '.mp', 'tcu', 'tse', 'stf', 'stj',
        'g1.globo.com', 'oglobo.globo.com', 'folha.com.br',
        'estadao.com.br', 'valor.com.br', 'poder360.com.br',
        'congressoemfoco.uol.com.br', 'metropoles.com'
    ]
    
    # Pontuação de relevância
    pontuacao = 0
    
    # Bônus por fonte confiável
    if any(fonte in href for fonte in fontes_preferenciais):
        pontuacao += 3
    
    # Bônus por termos jurídicos/importantes
    termos_importantes = [
        'processo', 'ação', 'tribunal', 'ministério público', 'justiça',
        'condenação', 'prisão', 'investigação', 'denúncia', 'licitação',
        'contrato', 'desvio', 'corrupção', 'fraude'
    ]
    
    texto_completo = f"{title} {body}"
    for termo in termos_importantes:
        if termo in texto_completo:
            pontuacao += 1
    
    # Penalizar por irrelevância
    termos_irrelevantes = [
        'receita federal', 'nota fiscal', 'certidão', 'agendamento',
        'marcar horário', 'agendar', 'consulta simples'
    ]
    
    for termo in termos_irrelevantes:
        if termo in texto_completo:
            pontuacao -= 2
    
    return pontuacao >= 1  # Pelo menos um critério de relevância

def _filtrar_resultados_inteligente(resultados, nome_pessoa):
    """Filtragem inteligente para remover duplicatas e irrelevâncias"""
    resultados_unicos = []
    urls_vistas = set()
    conteudos_similares = set()
    
    nome_pattern = re.compile(re.escape(nome_pessoa.lower()))
    
    for resultado in resultados:
        url = resultado.get('href', '')
        title = resultado.get('title', '').lower()
        body = resultado.get('body', '').lower()
        
        # Pular URLs duplicadas
        if url in urls_vistas:
            continue
        
        # Verificar se o nome aparece no resultado
        texto_completo = f"{title} {body}"
        if not nome_pattern.search(texto_completo):
            continue  # Pular se não menciona o nome
        
        # Detectar conteúdo similar (evitar notícias duplicadas)
        hash_conteudo = hash(title[:100])  # Hash do título como identificador
        if hash_conteudo in conteudos_similares:
            continue
        
        urls_vistas.add(url)
        conteudos_similares.add(hash_conteudo)
        resultados_unicos.append(resultado)
    
    # Ordenar por relevância (fontes oficiais primeiro)
    resultados_unicos.sort(key=lambda x: _calcular_peso_relevancia(x))
    
    return resultados_unicos

def _calcular_peso_relevancia(resultado):
    """Calcula peso de relevância para ordenação"""
    href = resultado.get('href', '').lower()
    peso = 0
    
    # Fontes oficiais têm máxima prioridade
    if any(dominio in href for dominio in ['.gov', '.jus', '.mp', 'tcu', 'tse']):
        peso += 100
    
    # Fontes jornalísticas confiáveis
    elif any(dominio in href for dominio in ['g1.globo.com', 'oglobo.globo.com', 'folha.com.br']):
        peso += 50
    
    # Conteúdo jurídico tem alta prioridade
    title_body = f"{resultado.get('title', '')} {resultado.get('body', '')}".lower()
    if any(termo in title_body for termo in ['processo', 'tribunal', 'ministério público']):
        peso += 30
    
    return peso