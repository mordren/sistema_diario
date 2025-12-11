# reset_postgres.py
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text

from app import app, db
from models import AnalisePessoaDB, PolemicaDB, EmpresaAssociadaDB

load_dotenv()

def reset_postgres():
    """Reseta as tabelas específicas do PostgreSQL"""
    with app.app_context():
        try:
            print("🗑️  Dropando tabelas do PostgreSQL...")
            
            # Desabilitar constraints temporariamente
            db.session.execute(text('DROP TABLE IF EXISTS empresa_associada CASCADE'))
            db.session.execute(text('DROP TABLE IF EXISTS polemica CASCADE'))
            db.session.execute(text('DROP TABLE IF EXISTS analise_pessoa CASCADE'))
            
            db.session.commit()
            print("✅ Tabelas removidas")
            
            # Criar todas as tabelas novamente
            print("🔨 Criando novas tabelas...")
            db.create_all()
            
            print("✅ Banco PostgreSQL recriado com sucesso!")
            
            # Verificar as tabelas criadas
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            
            tables = [row[0] for row in result]
            print("📊 Tabelas criadas:", tables)
            
        except Exception as e:
            print(f"❌ Erro ao resetar PostgreSQL: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    confirm = input("⚠️  ATENÇÃO: Isso vai APAGAR TODOS os dados do PostgreSQL. Continuar? (s/N): ")
    if confirm.lower() == 's':
        reset_postgres()
    else:
        print("Operação cancelada.")