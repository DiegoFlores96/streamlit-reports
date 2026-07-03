"""Configuração e fixtures para testes."""
import os
import sys
import pytest
from pathlib import Path
from datetime import datetime
import time

# Adiciona o diretório raiz ao path para importações
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configuração de variáveis de ambiente para testes
os.environ.setdefault('JWT_SECRET_KEY', 'test-secret-key-12345')
os.environ.setdefault('JWT_EXPIRE_MINUTES', '60')


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Fixture que cria um banco de dados SQLite temporário para testes com todas as tabelas."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from model.TabUsuarios import Base, Usuario
    from model.TabEmpresa import TabEmpresa
    from model.TokenSessao import TokenSessao
    from model.DashboardItem import DashboardItem
    from model.SetorDashboard import SetorDashboard
    from model.UsuarioDashboardAcesso import UsuarioDashboardAcesso
    from model.UsuarioSetorAcesso import UsuarioSetorAcesso
    
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    
    # Cria engine e tabelas
    engine = create_engine(
        db_url,
        echo=False,
        connect_args={"timeout": 30, "check_same_thread": False},
        poolclass=NullPool,
    )
    
    # Cria todas as tabelas
    Base.metadata.create_all(engine)
    
    # Cria session maker
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Insere empresa padrão (necessária para FK)
    timestamp = int(time.time())
    empresa_padrao = TabEmpresa(
        nome="Empresa Teste",
        cnpj="12.345.678/0001-00",
        ativo=True,
        dt_criacao=timestamp,
        dt_atualizacao=timestamp
    )
    session.add(empresa_padrao)
    session.commit()
    
    yield session
    
    # Cleanup
    session.close()
    engine.dispose()


@pytest.fixture
def mock_streamlit_session():
    """Fixture que mock da session state do Streamlit."""
    import streamlit as st
    
    # Salva estado anterior
    previous_state = dict(st.session_state)
    
    # Limpa session
    st.session_state.clear()
    
    yield st.session_state
    
    # Restaura estado anterior
    st.session_state.clear()
    st.session_state.update(previous_state)


@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup executado após cada teste."""
    yield
    # Pode adicionar limpeza global aqui se necessário
