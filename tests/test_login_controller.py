"""Testes para Login Controller."""
import pytest
from controller.loginController import LoginController
from model.TabUsuarios import Usuario


class TestLoginController:
    """Testes para autenticação e gerenciamento de usuários."""

    def setup_method(self):
        """Setup executado antes de cada teste."""
        self.controller = LoginController()

    def test_hash_password_não_vazio(self):
        """Testa que hash de senha não é vazio."""
        password = "SenhaForte123!"
        hashed = LoginController._hash_password(password)
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password  # Hash não pode ser igual à senha

    def test_hash_password_bcrypt_format(self):
        """Testa que hash segue formato bcrypt."""
        password = "SenhaForte123!"
        hashed = LoginController._hash_password(password)
        
        # Hash bcrypt começa com $2a$, $2b$, $2x$ ou $2y$
        assert hashed.startswith('$2'), "Hash deve ser bcrypt format"

    def test_hash_passwords_diferentes_geram_hashes_diferentes(self):
        """Testa que mesma senha gera hashes diferentes (bcrypt adiciona salt)."""
        password = "SenhaForte123!"
        hash1 = LoginController._hash_password(password)
        hash2 = LoginController._hash_password(password)
        
        # Bcrypt com salt aleatório gera hashes diferentes
        assert hash1 != hash2, "Bcrypt deve gerar hashes diferentes mesmo para mesma senha"

    def test_verify_password_válido(self):
        """Testa verificação de senha válida."""
        password = "SenhaForte123!"
        hashed = LoginController._hash_password(password)
        
        assert LoginController._verify_password(password, hashed) is True

    def test_verify_password_inválido(self):
        """Testa verificação de senha incorreta."""
        password = "SenhaForte123!"
        wrong_password = "SenhaErrada456"
        hashed = LoginController._hash_password(password)
        
        assert LoginController._verify_password(wrong_password, hashed) is False

    def test_verify_password_compatibilidade_sha256_legado(self):
        """Testa compatibilidade com hashes SHA256 antigos."""
        import hashlib
        password = "SenhaAntigaSHA256"
        # Cria hash legado SHA256
        legacy_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Deve funcionar compatibilidade
        assert LoginController._verify_password(password, legacy_hash) is True
        # Senha errada deve falhar
        assert LoginController._verify_password("outraSenha", legacy_hash) is False

    def test_register_user_email_vazio_falha(self):
        """Testa que registro com email vazio falha."""
        sucesso, mensagem = self.controller.register_user(
            email="",
            senha="SenhaForte123!",
            nome="João Silva"
        )
        
        assert sucesso is False
        assert "email" in mensagem.lower()

    def test_register_user_nome_vazio_falha(self):
        """Testa que registro com nome vazio falha."""
        sucesso, mensagem = self.controller.register_user(
            email="joao@example.com",
            senha="SenhaForte123!",
            nome=""
        )
        
        assert sucesso is False
        assert "nome" in mensagem.lower()

    def test_register_user_senha_muito_curta_falha(self):
        """Testa que registro com senha < 8 caracteres falha."""
        sucesso, mensagem = self.controller.register_user(
            email="joao@example.com",
            senha="Abc123",  # Apenas 6 caracteres
            nome="João Silva"
        )
        
        assert sucesso is False
        assert "8" in mensagem or "caracteres" in mensagem.lower()

    def test_register_user_senha_sem_maiuscula_falha(self):
        """Testa que senha sem letra maiúscula falha."""
        sucesso, mensagem = self.controller.register_user(
            email="joao@example.com",
            senha="senhafraca123!",  # Sem maiúscula
            nome="João Silva"
        )
        
        assert sucesso is False
        assert "mai" in mensagem.lower() or "uppercase" in mensagem.lower()

    def test_register_user_senha_sem_numero_falha(self):
        """Testa que senha sem número falha."""
        sucesso, mensagem = self.controller.register_user(
            email="joao@example.com",
            senha="SenhaFraca!",  # Sem número
            nome="João Silva"
        )
        
        assert sucesso is False
        assert "número" in mensagem.lower() or "digit" in mensagem.lower()

    def test_init_session_valores_padrão(self):
        """Testa inicialização de sessão com valores padrão."""
        import streamlit as st
        
        # Limpa session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        LoginController.init_session()
        
        assert st.session_state.get('logged_in') is False
        assert st.session_state.get('id_usuario') is None
        assert st.session_state.get('email') == ""
        assert st.session_state.get('perfil') == "Padrao"

    def test_is_admin_false_por_padrão(self):
        """Testa que usuário padrão não é admin."""
        import streamlit as st
        st.session_state['perfil'] = 'Padrao'
        
        assert LoginController.is_admin() is False

    def test_is_admin_true_para_admin(self):
        """Testa que perfil admin retorna True."""
        import streamlit as st
        st.session_state['perfil'] = 'admin'
        
        assert LoginController.is_admin() is True

    def test_is_admin_case_insensitive(self):
        """Testa que verificação de admin é case-insensitive."""
        import streamlit as st
        
        st.session_state['perfil'] = 'ADMIN'
        assert LoginController.is_admin() is True
        
        st.session_state['perfil'] = 'Admin'
        assert LoginController.is_admin() is True
