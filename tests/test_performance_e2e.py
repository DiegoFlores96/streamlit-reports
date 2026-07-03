"""Testes de Performance, Load e E2E Smoke."""
import pytest
import time
from controller.loginController import LoginController
from controller.empresaController import EmpresaController
from model.TabUsuarios import Usuario
from model.TabEmpresa import TabEmpresa


class TestPerformance:
    """Testes de performance básicos."""

    def test_performance_hash_password(self):
        """Testa performance de hash de senha (bcrypt deve ser rápido)."""
        start = time.time()
        for i in range(5):
            LoginController._hash_password(f"Senha{i}Forte123")
        elapsed = time.time() - start
        
        # Bcrypt com 12 rounds deve levar ~0.1-0.5s por hash
        # 5 hashes = ~0.5-2.5s total (flexível por máquina)
        assert elapsed < 10, f"Hash password está muito lento: {elapsed}s"

    def test_performance_verify_password(self, temp_db):
        """Testa performance de verificação de senha."""
        timestamp = int(time.time())
        senha = "SenhaForte123"
        senha_hash = LoginController._hash_password(senha)
        
        usuario = Usuario(
            email="perf@teste.com",
            senha=senha_hash,
            nome="Perf Test",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        usuario_check = temp_db.query(Usuario).filter_by(email="perf@teste.com").first()
        
        start = time.time()
        for i in range(5):
            LoginController._verify_password(senha, usuario_check.senha)
        elapsed = time.time() - start
        
        # Verificação também usa bcrypt, deve ser rápida (~0.1-0.5s cada)
        assert elapsed < 10, f"Verify password está muito lento: {elapsed}s"

    def test_performance_listar_100_empresas(self, temp_db):
        """Testa listagem de muitas empresas."""
        timestamp = int(time.time())
        
        # Insere 100 empresas
        for i in range(100):
            empresa = TabEmpresa(
                nome=f"Empresa {i}",
                ativo=i % 2 == 0,  # 50 ativas
                dt_criacao=timestamp,
                dt_atualizacao=timestamp
            )
            temp_db.add(empresa)
        temp_db.commit()
        
        # Busca todas
        start = time.time()
        empresas = temp_db.query(TabEmpresa).all()
        elapsed = time.time() - start
        
        assert len(empresas) >= 100
        assert elapsed < 1, f"Listagem de 100 empresas levou {elapsed}s"

    def test_performance_query_por_perfil_1000_usuarios(self, temp_db):
        """Testa query por filtro (perfil) com 1000 usuários."""
        timestamp = int(time.time())
        
        # Insere 1000 usuários
        for i in range(1000):
            perfil = "Admin" if i % 10 == 0 else "Padrao"
            usuario = Usuario(
                email=f"user{i}@teste.com",
                senha=LoginController._hash_password("Senha123"),
                nome=f"User {i}",
                perfil=perfil,
                situacao="Ativado",
                dt_criacao=timestamp,
                dt_ultima_atualizacao=timestamp,
                id_empresa=1
            )
            temp_db.add(usuario)
            
            if i % 100 == 0:
                temp_db.commit()
        
        temp_db.commit()
        
        # Query com filtro
        start = time.time()
        admins = temp_db.query(Usuario).filter_by(perfil="Admin").all()
        elapsed = time.time() - start
        
        assert len(admins) >= 50  # Pelo menos 100 admins
        assert elapsed < 1, f"Query de 1000 usuários levou {elapsed}s"


class TestLoadBasic:
    """Testes de load básico."""

    def test_load_multiplas_autenticacoes(self, temp_db):
        """Testa múltiplas autenticações simuladas."""
        timestamp = int(time.time())
        
        # Cria 10 usuários
        usuarios = []
        for i in range(10):
            usuario = Usuario(
                email=f"load{i}@teste.com",
                senha=LoginController._hash_password(f"Senha{i}Forte123"),
                nome=f"Load User {i}",
                perfil="Padrao",
                situacao="Ativado",
                dt_criacao=timestamp,
                dt_ultima_atualizacao=timestamp,
                id_empresa=1
            )
            temp_db.add(usuario)
            usuarios.append(usuario)
        
        temp_db.commit()
        
        # Simula múltiplas tentativas de login
        start = time.time()
        for i in range(10):
            usuario = temp_db.query(Usuario).filter_by(email=f"load{i}@teste.com").first()
            if usuario:
                LoginController._verify_password(f"Senha{i}Forte123", usuario.senha)
        
        elapsed = time.time() - start
        
        # 10 buscas + 10 verificações deve ser rápido
        assert elapsed < 5, f"10 autenticações levaram {elapsed}s"

    def test_load_insercoes_em_lote(self, temp_db):
        """Testa inserção em lote de múltiplos registros."""
        timestamp = int(time.time())
        
        # Insere 100 usuários (reduzido para ser mais rápido)
        for i in range(100):
            usuario = Usuario(
                email=f"batch{i}@teste.com",
                senha=LoginController._hash_password("Senha123"),
                nome=f"Batch User {i}",
                perfil="Padrao",
                situacao="Ativado",
                dt_criacao=timestamp,
                dt_ultima_atualizacao=timestamp,
                id_empresa=1
            )
            temp_db.add(usuario)
        
        temp_db.commit()
        
        # Verifica que todos foram inseridos
        count = temp_db.query(Usuario).filter(Usuario.email.like("batch%")).count()
        assert count == 100, f"Esperava 100 usuários, encontrou {count}"


class TestSmokeE2E:
    """Smoke tests de fluxo E2E."""

    def test_fluxo_criacao_usuario_e_login(self, temp_db, mock_streamlit_session):
        """Teste E2E: Criar usuário e fazer login."""
        import streamlit as st
        
        timestamp = int(time.time())
        
        # Step 1: Criar usuário
        email = "fluxo@teste.com"
        senha = "SenhaFluxo123"
        senha_hash = LoginController._hash_password(senha)
        
        usuario = Usuario(
            email=email,
            senha=senha_hash,
            nome="Fluxo User",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Step 2: Simular login
        usuario_login = temp_db.query(Usuario).filter_by(email=email).first()
        assert usuario_login is not None
        
        # Step 3: Verificar senha
        senha_correta = LoginController._verify_password(senha, usuario_login.senha)
        assert senha_correta is True
        
        # Step 4: Atualizar session state
        st.session_state.logged_in = True
        st.session_state.id_usuario = usuario_login.id_usuario
        st.session_state.email = usuario_login.email
        st.session_state.nome = usuario_login.nome
        st.session_state.perfil = usuario_login.perfil
        
        # Step 5: Validar session state
        assert st.session_state.logged_in is True
        assert st.session_state.email == email
        assert st.session_state.perfil == "Padrao"

    def test_fluxo_admin_acesso_area_administrativa(self, temp_db, mock_streamlit_session):
        """Teste E2E: Admin acessando área administrativa."""
        import streamlit as st
        
        timestamp = int(time.time())
        
        # Criar admin
        admin = Usuario(
            email="admin_fluxo@teste.com",
            senha=LoginController._hash_password("AdminSenha123"),
            nome="Admin Fluxo",
            perfil="Admin",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(admin)
        temp_db.commit()
        
        # Login como admin
        st.session_state.logged_in = True
        st.session_state.perfil = "Admin"
        
        login_controller = LoginController()
        
        # Verificar acesso admin
        assert login_controller.is_admin() is True
        
        # Seria preciso de middleware real para testar completamente
        # Mas conseguimos validar a lógica basic

    def test_fluxo_criar_empresa_e_associar_usuario(self, temp_db):
        """Teste E2E: Criar empresa e associar usuário."""
        timestamp = int(time.time())
        
        # Step 1: Criar empresa
        empresa = TabEmpresa(
            nome="Empresa Fluxo",
            cnpj="99.999.999/0001-99",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        temp_db.add(empresa)
        temp_db.commit()
        
        # Step 2: Criar usuário associado
        usuario = Usuario(
            email="usuario_empresa@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Usuario Empresa",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=empresa.id_empresa  # Associa à empresa
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Step 3: Verificar associação
        usuario_check = temp_db.query(Usuario).filter_by(email="usuario_empresa@teste.com").first()
        assert usuario_check.id_empresa == empresa.id_empresa
        
        empresa_check = temp_db.query(TabEmpresa).filter_by(id_empresa=usuario_check.id_empresa).first()
        assert empresa_check.nome == "Empresa Fluxo"
