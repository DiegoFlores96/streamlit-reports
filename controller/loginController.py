"""Controlador de autenticação e gerenciamento de usuários.

Responsável por:
  - Autenticação de usuários (login/logout)
  - Registro de novos usuários
  - Gerenciamento de senhas (hash/verify)
  - Rate limiting (proteção contra brute force)
  - Persistência de sessão
  - Controle de acesso e perfis
"""
import logging
import bcrypt
from datetime import datetime
from sqlalchemy import and_
import streamlit as st
from db.conexao import Conexao
from model.DashboardItem import DashboardItem
from model.SetorDashboard import SetorDashboard
from model.TabUsuarios import Usuario
from model.UsuarioDashboardAcesso import UsuarioDashboardAcesso
from model.UsuarioSetorAcesso import UsuarioSetorAcesso
from typing import Optional, Tuple
from helpers.jwt_helper import JWTHelper
from helpers.session_persist import SessionPersist
from helpers.validators import email_valido, nome_valido, perfil_valido, senha_valida
from controller.token_controller import TokenController

# Configurar logger
logger = logging.getLogger(__name__)


class LoginController:
    """Gerencia autenticação, registro e controle de acesso de usuários."""
    
    # Rate limiting - proteção contra brute force
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300  # 5 minutos
    TOKEN_VALIDITY_MINUTES = 60
    
    # Valores padrão de sessão
    DEFAULT_PROFILE = "Padrao"
    DEFAULT_STATUS = "Ativado"
    
    def __init__(self):
        self.db = Conexao()

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using bcrypt (secure, salted hashing)."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        """Verify password against bcrypt hash (supports legacy SHA256).
        
        For backward compatibility, detects and supports SHA256 hashes,
        but will migrate to bcrypt on next password change.
        """
        try:
            # Check if it's a bcrypt hash (starts with $2a$, $2b$, $2x$, $2y$)
            if password_hash.startswith('$2'):
                return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
            # Fallback for legacy SHA256 hashes (for backward compatibility)
            else:
                import hashlib
                legacy_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
                return legacy_hash == password_hash
        except Exception:
            return False

    @staticmethod
    def init_session():
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
        if "id_usuario" not in st.session_state:
            st.session_state.id_usuario = None
        if "id_empresa" not in st.session_state:  # Inicializa o id_empresa na sessão
            st.session_state.id_empresa = None
        if "email" not in st.session_state:
            st.session_state.email = ""
        if "nome" not in st.session_state:
            st.session_state.nome = ""
        if "perfil" not in st.session_state:
            st.session_state.perfil = "Padrao"
        if "jwt_token" not in st.session_state:
            st.session_state.jwt_token = None
        if "auth_token" not in st.session_state:
            st.session_state.auth_token = None
        if "login_attempts" not in st.session_state:
            st.session_state.login_attempts = 0
        if "login_blocked_until" not in st.session_state:
            st.session_state.login_blocked_until = None

    @staticmethod
    def is_logged_in() -> bool:
        return bool(st.session_state.get("logged_in", False))

    @staticmethod
    def get_logged_user() -> str:
        return st.session_state.get("email", "")

    @staticmethod
    def get_logged_user_id() -> int | None:
        return st.session_state.get("id_usuario")

    @staticmethod
    def get_logged_user_name() -> str:
        return st.session_state.get("nome", "")

    @staticmethod
    def get_logged_user_profile() -> str:
        return st.session_state.get("perfil", "Padrao")

    @staticmethod
    def is_admin() -> bool:
        return (st.session_state.get("perfil", "Padrao") or "").lower() == "admin"

    def logout(self) -> None:
        token = st.session_state.get('auth_token') or st.session_state.get('jwt_token')
        if token:
            TokenController().desativar_token(token)
            SessionPersist.remover_token()

        st.session_state.logged_in = False
        st.session_state.id_usuario = None
        st.session_state.id_empresa = None  # Limpa o id_empresa no logout
        st.session_state.email = ""
        st.session_state.nome = ""
        st.session_state.perfil = "Padrao"
        st.session_state.auth_token = None
        st.session_state.jwt_token = None

        st.query_params.clear()

    def register_user(self, email: str, senha: str, nome: str, perfil: str = "Padrao") -> tuple[bool, str]:
        # Validar email
        email_ok, email_err = email_valido(email)
        if not email_ok:
            return False, email_err
        
        # Validar nome
        nome_ok, nome_err = nome_valido(nome, min_len=2)
        if not nome_ok:
            return False, nome_err
        
        # Validar senha
        senha_ok, senha_err = senha_valida(senha)
        if not senha_ok:
            return False, senha_err
        
        # Validar perfil
        perfil_ok, perfil_err = perfil_valido(perfil or "Padrao")
        if not perfil_ok:
            return False, perfil_err
        
        perfil = (perfil or "Padrao").strip().title()

        session = self.db.get_session()
        try:
            usuario_existe = session.query(Usuario).filter_by(email=email).first()
            if usuario_existe:
                return False, "Email já cadastrado."

            novo_usuario = Usuario(
                email=email,
                senha=self._hash_password(senha),
                nome=nome,
                perfil=perfil,
                situacao="Ativado",
                dt_criacao=int(datetime.now().timestamp()),
                dt_utima_atualizacao=int(datetime.now().timestamp()),
                dt_desativacao=None,
            )
            session.add(novo_usuario)
            session.commit()
            return True, "Usuário criado com sucesso."

        except Exception as e:
            session.rollback()
            return False, f"Erro ao criar usuário: {str(e)}"
        finally:
            self.db.close_session(session)

    @staticmethod
    def _validate_rate_limit_and_record_attempt(should_record: bool = False) -> tuple[bool, str]:
        """Valida rate limit e opcionalmente registra tentativa falhada.
        
        Args:
            should_record: Se True, incrementa contador de tentativas
            
        Returns:
            (está_bloqueado, mensagem_erro)
        """
        import time
        
        blocked_until = st.session_state.get("login_blocked_until")
        
        # Verificar se ainda está bloqueado
        if blocked_until and time.time() < blocked_until:
            remaining = int(blocked_until - time.time())
            return True, f"Muitas tentativas. Aguarde {remaining} segundos."
        
        # Desbloquear se tempo expirou
        if blocked_until and time.time() >= blocked_until:
            st.session_state.login_attempts = 0
            st.session_state.login_blocked_until = None
        
        # Registrar tentativa se solicitado
        if should_record:
            attempts = st.session_state.get("login_attempts", 0) + 1
            st.session_state.login_attempts = attempts
            
            if attempts >= LoginController.MAX_LOGIN_ATTEMPTS:
                st.session_state.login_blocked_until = time.time() + LoginController.LOCKOUT_SECONDS
        
        return False, ""

    @staticmethod
    def _check_rate_limit() -> tuple[bool, str]:
        """[DEPRECADO] Use _validate_rate_limit_and_record_attempt() - Mantido para compatibilidade"""
        return LoginController._validate_rate_limit_and_record_attempt(should_record=False)

    @staticmethod
    def _register_failed_attempt() -> None:
        """[DEPRECADO] Use _validate_rate_limit_and_record_attempt() - Mantido para compatibilidade"""
        LoginController._validate_rate_limit_and_record_attempt(should_record=True)

    def _set_session_from_usuario(self, usuario: Usuario, token: str) -> None:
        """Atualiza session state com dados do usuário após login bem-sucedido.
        
        Args:
            usuario: Objeto Usuario do banco de dados
            token: JWT token para a sessão
        """
        st.session_state.logged_in = True
        st.session_state.id_usuario = usuario.id_usuario
        st.session_state.email = usuario.email
        st.session_state.nome = usuario.nome
        st.session_state.perfil = usuario.perfil or self.DEFAULT_PROFILE
        st.session_state.auth_token = token
        st.session_state.id_empresa = usuario.id_empresa
        st.session_state.login_attempts = 0
        st.session_state.login_blocked_until = None
        st.query_params["id"] = str(usuario.id_usuario)

    def login(self, email: str, senha: str) -> tuple[bool, str]:
        """Autentica usuário com email e senha.
        
        Args:
            email: Email do usuário
            senha: Senha em texto plano
            
        Returns:
            (sucesso, mensagem)
        """
        # Validação básica de email
        email_ok, email_err = email_valido(email)
        if not email_ok:
            return False, email_err

        blocked, msg = self._validate_rate_limit_and_record_attempt(should_record=False)
        if blocked:
            return False, msg

        session = self.db.get_session()

        try:
            usuario = session.query(Usuario).filter_by(email=email).first()

            if not usuario:
                self._validate_rate_limit_and_record_attempt(should_record=True)
                # Mensagem genérica para prevenir user enumeration
                return False, "Credenciais inválidas. Verifique email e senha."

            if (usuario.situacao or "").lower() != self.DEFAULT_STATUS.lower():
                return False, "Sua conta foi desativada. Entre em contato com o administrador."

            # Verificação segura de senha (suporta bcrypt e legacy SHA256)
            if not self._verify_password(senha, usuario.senha):
                self._validate_rate_limit_and_record_attempt(should_record=True)
                return False, "Credenciais inválidas. Verifique email e senha."

            # Criar token JWT e salvar sessão
            token = JWTHelper.criar_token(usuario.id_usuario)
            token_controller = TokenController()
            token_controller.salvar_token(usuario.id_usuario, token, self.TOKEN_VALIDITY_MINUTES)

            # Atualizar session state
            self._set_session_from_usuario(usuario, token)
            st.rerun()

            return True, "Login realizado com sucesso."

        except Exception as e:
            return False, f"Erro ao fazer login: {str(e)}"
        finally:
            self.db.close_session(session)

    def restaurar_sessao_apos_f5(self) -> bool:
        if self.is_logged_in():
            return True

        token = SessionPersist.recuperar_token()

        if not token:
            return False

        token_controller = TokenController()
        dados_token = token_controller.validar_token(token)

        if not dados_token:
            SessionPersist.remover_token()
            return False

        session = self.db.get_session()
        try:
            usuario = session.query(Usuario).filter_by(
                id_usuario=dados_token['id_usuario']
            ).first()

            if not usuario:
                SessionPersist.remover_token()
                return False

            if (usuario.situacao or "").lower() != "ativado":
                SessionPersist.remover_token()
                return False

            # Restaura a sessão recuperando todos os parâmetros originais
            st.session_state.logged_in = True
            st.session_state.id_usuario = usuario.id_usuario
            st.session_state.id_empresa = usuario.id_empresa
            st.session_state.email = usuario.email
            st.session_state.nome = usuario.nome
            st.session_state.perfil = usuario.perfil or "Padrao"
            st.session_state.auth_token = token
            st.session_state.session_restored = True

            return True

        except Exception as e:
            logger.warning(f"Erro ao restaurar sessão (continuando com login fresco)", exc_info=False)
            return False
        finally:
            self.db.close_session(session)

    def list_users(self) -> list[Usuario]:
        session = self.db.get_session()
        try:
            return session.query(Usuario).order_by(Usuario.nome).all()
        finally:
            self.db.close_session(session)

    def update_user(self, id_usuario: int, nome: str, perfil: str, situacao: str) -> tuple[bool, str]:
        # Validar nome
        nome_ok, nome_err = nome_valido(nome, min_len=2)
        if not nome_ok:
            return False, nome_err
        
        # Validar perfil
        perfil_ok, perfil_err = perfil_valido(perfil or "Padrao")
        if not perfil_ok:
            return False, perfil_err
        
        session = self.db.get_session()
        try:
            usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
            if not usuario:
                return False, "Usuário não encontrado."

            usuario.nome = nome.strip()
            usuario.perfil = (perfil or "Padrao").strip().title()
            usuario.situacao = (situacao or "Ativado").strip().title()
            usuario.dt_utima_atualizacao = int(datetime.now().timestamp())
            if (usuario.situacao or "").lower() == "desativado" and not usuario.dt_desativacao:
                usuario.dt_desativacao = int(datetime.now().timestamp())
            if (usuario.situacao or "").lower() == "ativado":
                usuario.dt_desativacao = None
            session.commit()
            return True, "Usuário atualizado com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao atualizar usuário: {str(e)}"
        finally:
            self.db.close_session(session)

    def deactivate_user(self, id_usuario: int) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
            if not usuario:
                return False, "Usuário não encontrado."

            usuario.situacao = "Desativado"
            usuario.dt_desativacao = int(datetime.now().timestamp())
            usuario.dt_utima_atualizacao = int(datetime.now().timestamp())
            session.commit()
            return True, "Usuário desativado com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao desativar usuário: {str(e)}"
        finally:
            self.db.close_session(session)

    def create_setor(self, nome_setor: str) -> tuple[bool, str]:
        nome_setor = nome_setor.strip()
        if not nome_setor:
            return False, "Informe o nome do setor."

        session = self.db.get_session()
        try:
            exists = session.query(SetorDashboard).filter_by(nome_setor=nome_setor).first()
            if exists:
                return False, "Setor já existe."

            setor = SetorDashboard(nome_setor=nome_setor, situacao="Ativado")
            session.add(setor)
            session.commit()
            return True, "Setor criado com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao criar setor: {str(e)}"
        finally:
            self.db.close_session(session)

    def list_setores(self) -> list[SetorDashboard]:
        session = self.db.get_session()
        try:
            return session.query(SetorDashboard).order_by(SetorDashboard.nome_setor).all()
        finally:
            self.db.close_session(session)

    def add_user_setor(self, id_usuario, id_setor):
        ids_atuais = self.get_user_allowed_setor_ids(id_usuario)
        if id_setor not in ids_atuais:
            ids_atuais.append(id_setor)
        return self.grant_setor_access(id_usuario, ids_atuais)

    def remove_user_setor(self, id_usuario, id_setor):
        ids_atuais = self.get_user_allowed_setor_ids(id_usuario)
        novos_ids = [x for x in ids_atuais if x != id_setor]
        return self.grant_setor_access(id_usuario, novos_ids)

    def create_dashboard(
            self,
            nome_dashboard: str,
            descricao: str,
            id_setor: int,
            tipo_pagina: str = "dashboard",
            codigo_pagina: str = "dashboard_exemplo",
    ) -> tuple[bool, str]:
        nome_dashboard = nome_dashboard.strip()
        if not nome_dashboard:
            return False, "Informe o nome do dashboard."

        session = self.db.get_session()
        try:
            dash = DashboardItem(
                nome_dashboard=nome_dashboard,
                descricao=descricao.strip(),
                tipo_pagina=(tipo_pagina or "dashboard").strip().lower(),
                codigo_pagina=(codigo_pagina or "dashboard_exemplo").strip().lower(),
                id_setor=id_setor,
                ativo=True,
            )
            session.add(dash)
            session.commit()
            return True, "Dashboard criado com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao criar dashboard: {str(e)}"
        finally:
            self.db.close_session(session)

    def list_dashboards(self) -> list[DashboardItem]:
        session = self.db.get_session()
        try:
            return session.query(DashboardItem).order_by(DashboardItem.nome_dashboard).all()
        finally:
            self.db.close_session(session)

    def grant_dashboard_access(self, id_usuario: int, dashboard_ids: list[int]) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            session.query(UsuarioDashboardAcesso).filter_by(id_usuario=id_usuario).delete()

            for id_dashboard in dashboard_ids:
                session.add(
                    UsuarioDashboardAcesso(id_usuario=id_usuario, id_dashboard=id_dashboard)
                )

            session.commit()
            return True, "Permissões atualizadas com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao atualizar permissões: {str(e)}"
        finally:
            self.db.close_session(session)

    def grant_setor_access(self, id_usuario: int, setor_ids: list[int]) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            session.query(UsuarioSetorAcesso).filter_by(id_usuario=id_usuario).delete()
            for id_setor in setor_ids:
                session.add(UsuarioSetorAcesso(id_usuario=id_usuario, id_setor=id_setor))
            session.commit()
            return True, "Setores do usuário atualizados com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao atualizar setores do usuário: {str(e)}"
        finally:
            self.db.close_session(session)

    def get_user_allowed_setor_ids(self, id_usuario: int) -> list[int]:
        session = self.db.get_session()
        try:
            rows = session.query(UsuarioSetorAcesso.id_setor).filter_by(id_usuario=id_usuario).all()
            return [r.id_setor for r in rows]
        finally:
            self.db.close_session(session)

    def get_user_allowed_pages(self, id_usuario: int) -> list[dict]:
        session = self.db.get_session()
        try:
            rows = (
                session.query(
                    DashboardItem.id_dashboard,
                    DashboardItem.nome_dashboard,
                    DashboardItem.descricao,
                    DashboardItem.tipo_pagina,
                    DashboardItem.codigo_pagina,
                    SetorDashboard.nome_setor,
                )
                .join(UsuarioDashboardAcesso, UsuarioDashboardAcesso.id_dashboard == DashboardItem.id_dashboard)
                .join(SetorDashboard, SetorDashboard.id_setor == DashboardItem.id_setor)
                .join(
                    UsuarioSetorAcesso,
                    and_(
                        UsuarioSetorAcesso.id_usuario == UsuarioDashboardAcesso.id_usuario,
                        UsuarioSetorAcesso.id_setor == DashboardItem.id_setor,
                    ),
                )
                .filter(UsuarioDashboardAcesso.id_usuario == id_usuario)
                .filter(DashboardItem.ativo == True)
                .order_by(SetorDashboard.nome_setor, DashboardItem.nome_dashboard)
                .all()
            )

            return [
                {
                    "id_dashboard": row.id_dashboard,
                    "nome_dashboard": row.nome_dashboard,
                    "descricao": row.descricao,
                    "tipo_pagina": row.tipo_pagina,
                    "codigo_pagina": row.codigo_pagina,
                    "setor": row.nome_setor,
                }
                for row in rows
            ]
        finally:
            self.db.close_session(session)

    def get_menu_pages_for_logged_user(self) -> list[dict]:
        user_id = self.get_logged_user_id()
        if user_id is None:
            return []

        if self.is_admin():
            session = self.db.get_session()
            try:
                rows = (
                    session.query(
                        DashboardItem.id_dashboard,
                        DashboardItem.nome_dashboard,
                        DashboardItem.descricao,
                        DashboardItem.tipo_pagina,
                        DashboardItem.codigo_pagina,
                        SetorDashboard.nome_setor,
                    )
                    .join(SetorDashboard, SetorDashboard.id_setor == DashboardItem.id_setor)
                    .filter(DashboardItem.ativo == True)
                    .order_by(SetorDashboard.nome_setor, DashboardItem.nome_dashboard)
                    .all()
                )
                return [
                    {
                        "id_dashboard": row.id_dashboard,
                        "nome_dashboard": row.nome_dashboard,
                        "descricao": row.descricao,
                        "tipo_pagina": row.tipo_pagina,
                        "codigo_pagina": row.codigo_pagina,
                        "setor": row.nome_setor,
                    }
                    for row in rows
                ]
            finally:
                self.db.close_session(session)

        return self.get_user_allowed_pages(user_id)

    def get_user_allowed_dashboards(self, id_usuario: int) -> list[dict]:
        return self.get_user_allowed_pages(id_usuario)