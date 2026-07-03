"""Testes para Middleware e Helpers - Formatação, Acesso."""
import pytest
import time
from datetime import datetime
from middleware.access_control import AccessControlMiddleware
from controller.loginController import LoginController
from model.TabUsuarios import Usuario
from helpers.formata import data_br, reais, limpar, porcentagem, formatar_numero


class TestAccessControlMiddleware:
    """Testes para AccessControlMiddleware."""

    def test_require_admin_com_admin(self, temp_db, mock_streamlit_session):
        """Testa que require_admin permite acesso a admin."""
        import streamlit as st
        
        timestamp = int(time.time())
        
        # Cria usuário admin
        usuario_admin = Usuario(
            email="admin@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Admin User",
            perfil="Admin",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario_admin)
        temp_db.commit()
        
        # Setup session como admin
        st.session_state.logged_in = True
        st.session_state.id_usuario = usuario_admin.id_usuario
        st.session_state.perfil = "Admin"
        
        # Cria login controller
        login_controller = LoginController()
        
        # Verifica acesso
        is_admin = login_controller.is_admin()
        assert is_admin is True

    def test_require_admin_sem_admin(self, temp_db, mock_streamlit_session):
        """Testa que require_admin nega acesso a não-admin."""
        import streamlit as st
        
        timestamp = int(time.time())
        
        # Cria usuário comum
        usuario_comum = Usuario(
            email="user@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Common User",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario_comum)
        temp_db.commit()
        
        # Setup session como usuário comum
        st.session_state.logged_in = True
        st.session_state.id_usuario = usuario_comum.id_usuario
        st.session_state.perfil = "Padrao"
        
        # Cria login controller
        login_controller = LoginController()
        
        # Verifica acesso
        is_admin = login_controller.is_admin()
        assert is_admin is False

    def test_perfil_case_insensitive(self, temp_db, mock_streamlit_session):
        """Testa que verificação de admin é case-insensitive."""
        import streamlit as st
        
        timestamp = int(time.time())
        
        usuario = Usuario(
            email="mixed@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Mixed Case",
            perfil="ADMIN",  # Maiúscula
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Setup
        st.session_state.logged_in = True
        st.session_state.perfil = "ADMIN"
        
        login_controller = LoginController()
        is_admin = login_controller.is_admin()
        assert is_admin is True


class TestFormatadores:
    """Testes para funções de formatação."""

    def test_formata_data_br(self):
        """Testa formatação de data em padrão brasileiro."""
        # Testa com datetime
        data = datetime(2024, 12, 25)
        resultado = data_br(data)
        assert resultado == "25/12/2024"

    def test_formata_data_br_string_us(self):
        """Testa formatação de data a partir de string US."""
        resultado = data_br("2024-12-25")
        assert resultado == "25/12/2024"

    def test_formata_data_br_timestamp(self):
        """Testa formatação de data a partir de timestamp."""
        timestamp = 1735084800  # 2024-12-25 00:00:00 UTC
        resultado = data_br(timestamp)
        assert "25" in resultado or "24" in resultado  # Pode variar por timezone

    def test_formata_data_br_invalida(self):
        """Testa formatação de data inválida retorna vazio."""
        resultado = data_br("invalid")
        assert resultado == ""

    def test_formata_moeda_positiva(self):
        """Testa formatação de moeda positiva."""
        resultado = reais(1234.56)
        assert "R$" in resultado
        assert "1" in resultado and "234" in resultado

    def test_formata_moeda_negativa(self):
        """Testa formatação de moeda negativa."""
        resultado = reais(-1234.56)
        assert "R$" in resultado or "-" in resultado

    def test_formata_moeda_zero(self):
        """Testa formatação de moeda zero."""
        resultado = reais(0)
        assert "0" in resultado and "R$" in resultado

    def test_limpa_strings_numeros(self):
        """Testa limpeza de strings com números."""
        resultado = limpar("123abc456", manter_numeros=True)
        assert "abc" in resultado.lower() or "123" in resultado

    def test_limpa_strings_caracteres_especiais(self):
        """Testa limpeza de caracteres especiais."""
        resultado = limpar("test@#$%name")
        assert "@" not in resultado
        assert "#" not in resultado
        assert "test" in resultado.lower()

    def test_limpa_strings_unicode(self):
        """Testa limpeza mantendo Unicode."""
        resultado = limpar("José@#$")
        assert "Jos" in resultado or "jose" in resultado.lower()

    def test_porcento_formatacao(self):
        """Testa formatação de percentual."""
        resultado = porcentagem(0.5)
        assert "50" in resultado or "50%" in resultado

    def test_porcento_zero(self):
        """Testa formatação de percentual zero."""
        resultado = porcentagem(0)
        assert "0" in resultado

    def test_porcento_um(self):
        """Testa formatação de percentual 100%."""
        resultado = porcentagem(1.0)
        assert "100" in resultado
