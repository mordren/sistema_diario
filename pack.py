import requests
import json
import time
import csv
from typing import List, Dict, Optional

class ProcessadorLote:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def carregar_lista_csv(self, arquivo_csv: str) -> List[Dict]:
        """Carrega lista de pesquisas de um arquivo CSV"""
        pesquisas = []
        try:
            with open(arquivo_csv, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    pesquisas.append({
                        'nome': row['nome'],
                        'cargo': row.get('cargo', '')
                    })
            print(f"✅ Carregadas {len(pesquisas)} pesquisas do CSV")
            return pesquisas
        except Exception as e:
            print(f"❌ Erro ao carregar CSV: {e}")
            return []
    
    def carregar_lista_json(self, arquivo_json: str) -> List[Dict]:
        """Carrega lista de pesquisas de um arquivo JSON"""
        try:
            with open(arquivo_json, 'r', encoding='utf-8') as file:
                dados = json.load(file)
                print(f"✅ Carregadas {len(dados)} pesquisas do JSON")
                return dados
        except Exception as e:
            print(f"❌ Erro ao carregar JSON: {e}")
            return []
    
    def executar_analise(self, nome: str, cargo: str = "") -> Dict:
        """Executa uma análise individual via API"""
        url = f"{self.base_url}/api/analises"
        payload = {
            "nome": nome,
            "cargo": cargo
        }
        
        try:
            print(f"🔍 Processando: {nome}" + (f" - {cargo}" if cargo else ""))
            
            response = self.session.post(
                url, 
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120  # 2 minutos timeout
            )
            
            if response.status_code == 201:
                resultado = response.json()
                print(f"✅ Sucesso: {nome} (ID: {resultado.get('id', 'N/A')})")
                return {
                    "status": "sucesso",
                    "nome": nome,
                    "cargo": cargo,
                    "analise_id": resultado.get("id"),
                    "risco_reputacao": resultado.get("analise", {}).get("risco_reputacao", "N/A"),
                    "total_polemicas": resultado.get("analise", {}).get("total_polemicas", 0),
                    "resposta": resultado
                }
            else:
                erro = response.json().get("error", "Erro desconhecido")
                print(f"❌ Erro na análise de {nome}: {erro}")
                return {
                    "status": "erro",
                    "nome": nome,
                    "cargo": cargo,
                    "erro": erro,
                    "status_code": response.status_code
                }
                
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout na análise de {nome}")
            return {
                "status": "timeout",
                "nome": nome,
                "cargo": cargo,
                "erro": "Timeout após 120 segundos"
            }
        except Exception as e:
            print(f"❌ Erro de conexão com {nome}: {e}")
            return {
                "status": "erro_conexao",
                "nome": nome,
                "cargo": cargo,
                "erro": str(e)
            }
    
    def processar_lote(self, pesquisas: List[Dict], delay: float = 2.0) -> Dict:
        """Processa um lote de pesquisas com delay entre requisições"""
        resultados = {
            "total": len(pesquisas),
            "sucessos": 0,
            "erros": 0,
            "timeouts": 0,
            "resultados": []
        }
        
        print(f"\n🚀 INICIANDO PROCESSAMENTO EM LOTE")
        print(f"📊 Total de pesquisas: {len(pesquisas)}")
        print(f"⏰ Delay entre requisições: {delay}s")
        print("=" * 50)
        
        for i, pesquisa in enumerate(pesquisas, 1):
            nome = pesquisa['nome']
            cargo = pesquisa.get('cargo', '')
            
            print(f"\n[{i}/{len(pesquisas)}] Processando...")
            
            # Executar análise
            resultado = self.executar_analise(nome, cargo)
            resultados["resultados"].append(resultado)
            
            # Atualizar contadores
            if resultado["status"] == "sucesso":
                resultados["sucessos"] += 1
            elif resultado["status"] == "timeout":
                resultados["timeouts"] += 1
            else:
                resultados["erros"] += 1
            
            # Delay entre requisições (evitar sobrecarga)
            if i < len(pesquisas):  # Não esperar após a última
                print(f"⏳ Aguardando {delay} segundos...")
                time.sleep(delay)
        
        return resultados
    
    def salvar_resultados(self, resultados: Dict, arquivo_saida: str):
        """Salva os resultados em um arquivo JSON"""
        try:
            with open(arquivo_saida, 'w', encoding='utf-8') as file:
                json.dump(resultados, file, ensure_ascii=False, indent=2)
            print(f"💾 Resultados salvos em: {arquivo_saida}")
        except Exception as e:
            print(f"❌ Erro ao salvar resultados: {e}")
    
    def gerar_relatorio_csv(self, resultados: Dict, arquivo_csv: str):
        """Gera um relatório CSV resumido"""
        try:
            with open(arquivo_csv, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Nome', 'Cargo', 'Status', 'ID Análise', 'Risco', 'Polêmicas', 'Erro'])
                
                for resultado in resultados["resultados"]:
                    writer.writerow([
                        resultado['nome'],
                        resultado.get('cargo', ''),
                        resultado['status'],
                        resultado.get('analise_id', ''),
                        resultado.get('risco_reputacao', ''),
                        resultado.get('total_polemicas', ''),
                        resultado.get('erro', '')
                    ])
            print(f"📄 Relatório CSV salvo em: {arquivo_csv}")
        except Exception as e:
            print(f"❌ Erro ao gerar CSV: {e}")

def main():
    # Configurações
    BASE_URL = "http://localhost:5000"  # Altere se necessário
    DELAY_ENTRE_REQUISICOES = 2.0  # Segundos entre cada análise
    
    # Inicializar processador
    processador = ProcessadorLote(BASE_URL)
    
    # OPÇÃO 1: Lista manual de pesquisas
    # pesquisas_manual = [
    #     {"nome": "João Silva", "cargo": "Prefeito"},
    #     {"nome": "Maria Santos", "cargo": "Vereadora"},
    #     {"nome": "Pedro Oliveira", "cargo": "Secretário"},
    #     # Adicione mais pesquisas conforme necessário
    # ]
    
    # OPÇÃO 2: Carregar de arquivo CSV
    # pesquisas = processador.carregar_lista_csv("pesquisas.csv")
    
    
    pesquisas = processador.carregar_lista_json("pesquisas.json")
    
    # Usar lista manual (modifique conforme necessário)
    # pesquisas = pesquisas_manual
    
    if not pesquisas:
        print("❌ Nenhuma pesquisa para processar")
        return
    
    # Executar processamento em lote
    resultados = processador.processar_lote(pesquisas, DELAY_ENTRE_REQUISICOES)
    
    # Exibir resumo
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL DO LOTE")
    print("=" * 50)
    print(f"✅ Sucessos: {resultados['sucessos']}")
    print(f"❌ Erros: {resultados['erros']}")
    print(f"⏰ Timeouts: {resultados['timeouts']}")
    print(f"📋 Total processado: {resultados['total']}")
    
    # Salvar resultados
    processador.salvar_resultados(resultados, "resultados_lote.json")
    processador.gerar_relatorio_csv(resultados, "relatorio_lote.csv")
    
    # Exibir algumas análises bem-sucedidas
    print("\n🎯 PRINCIPAIS RESULTADOS:")
    for resultado in resultados["resultados"][:5]:  # Mostrar apenas os 5 primeiros
        if resultado["status"] == "sucesso":
            print(f"  • {resultado['nome']}: {resultado.get('risco_reputacao', 'N/A')} "
                  f"({resultado.get('total_polemicas', 0)} polêmicas)")

if __name__ == "__main__":
    main()