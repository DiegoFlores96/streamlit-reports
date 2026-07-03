"""Testes de integração com banco de dados."""
import pytest
import time
from datetime import datetime
from sqlalchemy import text

from model.TabUsuarios import Usuario
from model.TabEmpresa import TabEmpresa
from model.TokenSessao import TokenSessao
from model.DashboardItem import DashboardItem
from model.SetorDashboard import SetorDashboard
from model.UsuarioDashboardAcesso import UsuarioDashboardAcesso
from model.UsuarioSetorAcesso import UsuarioSetorAcesso
from controller.loginController import LoginController


class TestDatabaseIntegration:
    """Testes de integração com banco de dados SQLite."""

    # ==========================================
    # TESTES DE TABELA: TabEmpresa
    # ==========================================
    
    def test_criar_empresa(self, temp_db):
        """Testa criação de nova empresa."""
        timestamp = int(time.time())
        empresa = TabEmpresa(
            nome="Empresa Teste 2",
            cnpj="12.345.678/0001-01",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        
        temp_db.add(empresa)
        temp_db.commit()
        
        # Verifica se foi criada
        empresa_salva = temp_db.query(TabEmpresa).filter_by(cnpj="12.345.678/0001-01").first()
        assert empresa_salva is not None
        assert empresa_salva.nome == "Empresa Teste 2"
        assert empresa_salva.ativo is True

    def test_atualizar_empresa(self, temp_db):
        """Testa atualização de empresa."""
        timestamp = int(time.time())
        
        # Pega empresa padrão criada na fixture
        empresa = temp_db.query(TabEmpresa).first()
        assert empresa is not None
        
        # Atualiza
        empresa.nome = "Empresa Atualizada"
        empresa.tema_primario = "#ff0000"
        temp_db.commit()
        
        # Verifica atualização
        empresa_check = temp_db.query(TabEmpresa).filter_by(id_empresa=empresa.id_empresa).first()
        assert empresa_check.nome == "Empresa Atualizada"
        assert empresa_check.tema_primario == "#ff0000"

    def test_listar_empresas(self, temp_db):
        """Testa listagem de empresas."""
        timestamp = int(time.time())
        
        # Adiciona mais uma empresa
        empresa2 = TabEmpresa(
            nome="Empresa 3",
            cnpj="98.765.432/0001-99",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        temp_db.add(empresa2)
        temp_db.commit()
        
        # Lista
        empresas = temp_db.query(TabEmpresa).all()
        assert len(empresas) >= 2
        nomes = [e.nome for e in empresas]
        assert "Empresa Teste" in nomes

    # ==========================================
    # TESTES DE TABELA: TabUsuarios
    # ==========================================
    
    def test_criar_usuario(self, temp_db):
        """Testa criação de novo usuário com senha hashada."""
        timestamp = int(time.time())
        senha_hash = LoginController._hash_password("SenhaForte123")
        
        usuario = Usuario(
            email="teste@exemplo.com",
            senha=senha_hash,
            nome="Teste User",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1  # FK para empresa padrão
        )
        
        temp_db.add(usuario)
        temp_db.commit()
        
        # Verifica se foi criado
        usuario_salvo = temp_db.query(Usuario).filter_by(email="teste@exemplo.com").first()
        assert usuario_salvo is not None
        assert usuario_salvo.nome == "Teste User"
        assert usuario_salvo.perfil == "Padrao"
        # Verifica que senha foi hashada
        assert usuario_salvo.senha.startswith('$2')  # bcrypt hash

    def test_buscar_usuario_por_email(self, temp_db):
        """Testa busca de usuário por email."""
        timestamp = int(time.time())
        
        usuario = Usuario(
            email="busca@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Busca User",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Busca
        usuario_encontrado = temp_db.query(Usuario).filter_by(email="busca@teste.com").first()
        assert usuario_encontrado is not None
        assert usuario_encontrado.nome == "Busca User"

    def test_atualizar_usuario(self, temp_db):
        """Testa atualização de usuário."""
        timestamp = int(time.time())
        
        usuario = Usuario(
            email="atualizar@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Usuário Original",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Atualiza
        usuario.nome = "Usuário Atualizado"
        usuario.perfil = "Admin"
        temp_db.commit()
        
        # Verifica
        usuario_check = temp_db.query(Usuario).filter_by(email="atualizar@teste.com").first()
        assert usuario_check.nome == "Usuário Atualizado"
        assert usuario_check.perfil == "Admin"

    def test_verificar_senha_usuario(self, temp_db):
        """Testa verificação de senha de usuário."""
        timestamp = int(time.time())
        senha_correta = "SenhaForte123"
        senha_hash = LoginController._hash_password(senha_correta)
        
        usuario = Usuario(
            email="senha@teste.com",
            senha=senha_hash,
            nome="Teste Senha",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Busca e verifica
        usuario_salvo = temp_db.query(Usuario).filter_by(email="senha@teste.com").first()
        assert usuario_salvo is not None
        
        # Verifica senha correta
        assert LoginController._verify_password(senha_correta, usuario_salvo.senha)
        # Verifica senha incorreta
        assert not LoginController._verify_password("SenhaErrada123", usuario_salvo.senha)

    def test_usuario_email_unico(self, temp_db):
        """Testa que emails de usuários são únicos."""
        timestamp = int(time.time())
        
        usuario1 = Usuario(
            email="unico@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Usuário 1",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario1)
        temp_db.commit()
        
        # Tenta criar outro com mesmo email
        usuario2 = Usuario(
            email="unico@teste.com",
            senha=LoginController._hash_password("Senha456"),
            nome="Usuário 2",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario2)
        
        # Deve falhar por violação de constraint
        with pytest.raises(Exception):  # IntegrityError
            temp_db.commit()

    # ==========================================
    # TESTES DE TABELA: TokenSessao
    # ==========================================
    
    def test_criar_token_sessao(self, temp_db):
        """Testa criação de token de sessão."""
        timestamp = int(time.time())
        
        usuario = Usuario(
            email="token@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Usuário Token",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Cria token
        token_sessao = TokenSessao(
            id_usuario=usuario.id_usuario,
            token="jwt_token_12345_abcde",
            dt_criacao=timestamp,
            dt_expiracao=timestamp + 3600,
            ativo=True
        )
        temp_db.add(token_sessao)
        temp_db.commit()
        
        # Verifica
        token_salvo = temp_db.query(TokenSessao).filter_by(token="jwt_token_12345_abcde").first()
        assert token_salvo is not None
        assert token_salvo.id_usuario == usuario.id_usuario
        assert token_salvo.ativo is True

    def test_desativar_token_sessao(self, temp_db):
        """Testa desativação de token."""
        timestamp = int(time.time())
        
        usuario = Usuario(
            email="desat@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Usuário Desat",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Cria token
        token_sessao = TokenSessao(
            id_usuario=usuario.id_usuario,
            token="jwt_token_desat",
            dt_criacao=timestamp,
            dt_expiracao=timestamp + 3600,
            ativo=True
        )
        temp_db.add(token_sessao)
        temp_db.commit()
        
        # Desativa
        token_sessao.ativo = False
        temp_db.commit()
        
        # Verifica
        token_check = temp_db.query(TokenSessao).filter_by(token="jwt_token_desat").first()
        assert token_check.ativo is False

    # ==========================================
    # TESTES DE TABELA: SetorDashboard
    # ==========================================
    
    def test_criar_setor(self, temp_db):
        """Testa criação de setor de dashboard."""
        setor = SetorDashboard(
            nome_setor="Vendas",
            situacao="Ativado"
        )
        
        temp_db.add(setor)
        temp_db.commit()
        
        # Verifica
        setor_salvo = temp_db.query(SetorDashboard).filter_by(nome_setor="Vendas").first()
        assert setor_salvo is not None
        assert setor_salvo.nome_setor == "Vendas"

    # ==========================================
    # TESTES DE RELACIONAMENTOS
    # ==========================================
    
    def test_usuario_associado_empresa(self, temp_db):
        """Testa que usuário pode ser associado a uma empresa."""
        timestamp = int(time.time())
        
        # Pega empresa padrão
        empresa = temp_db.query(TabEmpresa).first()
        
        usuario = Usuario(
            email="empresa@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Usuário Empresa",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=empresa.id_empresa  # Associa à empresa
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Verifica relacionamento
        usuario_check = temp_db.query(Usuario).filter_by(email="empresa@teste.com").first()
        assert usuario_check.id_empresa == empresa.id_empresa

    def test_multiplos_tokens_por_usuario(self, temp_db):
        """Testa que um usuário pode ter múltiplos tokens."""
        timestamp = int(time.time())
        
        usuario = Usuario(
            email="multi@teste.com",
            senha=LoginController._hash_password("Senha123"),
            nome="Usuário Multi",
            perfil="Padrao",
            situacao="Ativado",
            dt_criacao=timestamp,
            dt_ultima_atualizacao=timestamp,
            id_empresa=1
        )
        temp_db.add(usuario)
        temp_db.commit()
        
        # Cria múltiplos tokens
        for i in range(3):
            token = TokenSessao(
                id_usuario=usuario.id_usuario,
                token=f"jwt_token_{i}",
                dt_criacao=timestamp,
                dt_expiracao=timestamp + 3600,
                ativo=True
            )
            temp_db.add(token)
        temp_db.commit()
        
        # Verifica
        tokens = temp_db.query(TokenSessao).filter_by(id_usuario=usuario.id_usuario).all()
        assert len(tokens) == 3

    # ==========================================
    # TESTES DE QUERIES COMPLEXAS
    # ==========================================
    
    def test_listar_usuarios_por_perfil(self, temp_db):
        """Testa listagem de usuários por perfil."""
        timestamp = int(time.time())
        
        # Cria usuários com perfis diferentes
        usuarios_data = [
            ("admin1@teste.com", "Admin User 1", "Admin"),
            ("admin2@teste.com", "Admin User 2", "Admin"),
            ("padrao@teste.com", "Padrao User", "Padrao"),
        ]
        
        for email, nome, perfil in usuarios_data:
            usuario = Usuario(
                email=email,
                senha=LoginController._hash_password("Senha123"),
                nome=nome,
                perfil=perfil,
                situacao="Ativado",
                dt_criacao=timestamp,
                dt_ultima_atualizacao=timestamp,
                id_empresa=1
            )
            temp_db.add(usuario)
        temp_db.commit()
        
        # Busca por perfil
        admins = temp_db.query(Usuario).filter_by(perfil="Admin").all()
        assert len(admins) == 2
        
        padraos = temp_db.query(Usuario).filter_by(perfil="Padrao").all()
        assert any(u.nome == "Padrao User" for u in padraos)

    def test_listar_usuarios_ativos(self, temp_db):
        """Testa listagem de usuários ativos."""
        timestamp = int(time.time())
        
        # Cria usuários ativos e inativos
        usuarios_data = [
            ("ativo1@teste.com", "Ativo 1", "Ativado"),
            ("ativo2@teste.com", "Ativo 2", "Ativado"),
            ("inativo@teste.com", "Inativo", "Desativado"),
        ]
        
        for email, nome, situacao in usuarios_data:
            usuario = Usuario(
                email=email,
                senha=LoginController._hash_password("Senha123"),
                nome=nome,
                perfil="Padrao",
                situacao=situacao,
                dt_criacao=timestamp,
                dt_ultima_atualizacao=timestamp,
                id_empresa=1
            )
            temp_db.add(usuario)
        temp_db.commit()
        
        # Busca ativos
        ativos = temp_db.query(Usuario).filter_by(situacao="Ativado").all()
        assert len(ativos) >= 2
        
        # Busca inativos
        inativos = temp_db.query(Usuario).filter_by(situacao="Desativado").all()
        assert any(u.nome == "Inativo" for u in inativos)
