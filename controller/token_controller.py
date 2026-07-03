"""Controller para gerenciamento de tokens no banco de dados."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from db.conexao import Conexao
from model.TokenSessao import TokenSessao
from sqlalchemy.orm import Session


class TokenController:
    """Gerencia tokens de sessão no banco de dados."""

    def __init__(self) -> None:
        """Inicializa o controller com conexão com banco."""
        self._db: Conexao = Conexao()

    @staticmethod
    def _timestamp_atual() -> int:
        """Retorna timestamp atual em segundos."""
        return int(datetime.now().timestamp())

    def salvar_token(
            self,
            id_usuario: int,
            token: str,
            minutos_validade: int
    ) -> bool:
        """
        Salva um novo token no banco de dados.
        """
        session: Session = self._db.get_session()
        try:
            # Desativa tokens antigos do mesmo usuário
            session.query(TokenSessao).filter_by(
                id_usuario=id_usuario,
                ativo=True
            ).update({"ativo": False})

            expiracao = self._timestamp_atual() + (minutos_validade * 60)

            novo_token = TokenSessao(
                id_usuario=id_usuario,
                token=token,
                dt_criacao=self._timestamp_atual(),
                dt_expiracao=expiracao,
                dt_ultimo_acesso=self._timestamp_atual(),
                ativo=True
            )
            session.add(novo_token)
            session.commit()
            return True

        except Exception as e:
            session.rollback()
            print(f"Erro ao salvar token: {e}")
            return False
        finally:
            self._db.close_session(session)

    def salvar_token_com_dias(
            self,
            id_usuario: int,
            token: str,
            dias_validade: int
    ) -> bool:
        """
        Salva token com validade em dias.
        """
        minutos = dias_validade * 24 * 60
        return self.salvar_token(id_usuario, token, minutos)

    def validar_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Valida um token no banco de dados.
        """
        session: Session = self._db.get_session()
        try:
            token_db = session.query(TokenSessao).filter_by(
                token=token,
                ativo=True
            ).first()

            if not token_db:
                return None

            # Verifica se expirou
            if token_db.dt_expiracao and self._timestamp_atual() > token_db.dt_expiracao:
                token_db.ativo = False
                session.commit()
                return None

            # Atualiza último acesso
            token_db.dt_ultimo_acesso = self._timestamp_atual()
            session.commit()

            return {'id_usuario': token_db.id_usuario, 'token_id': token_db.id_token}

        except Exception as e:
            print(f"Erro ao validar token: {e}")
            return None
        finally:
            self._db.close_session(session)

    def desativar_token(self, token: str) -> bool:
        """
        Desativa um token (logout).
        """
        session: Session = self._db.get_session()
        try:
            session.query(TokenSessao).filter_by(
                token=token,
                ativo=True
            ).update({"ativo": False})
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Erro ao desativar token: {e}")
            return False
        finally:
            self._db.close_session(session)

    def get_ultimo_token_usuario(self, id_usuario: int) -> Optional[str]:
        """Busca o último token ativo do usuário no banco"""
        session: Session = self._db.get_session()
        try:
            token_db = session.query(TokenSessao).filter_by(
                id_usuario=id_usuario,
                ativo=True
            ).order_by(TokenSessao.dt_criacao.desc()).first()

            if token_db:
                return token_db.token
            return None
        except Exception as e:
            print(f"Erro ao buscar token do usuário: {e}")
            return None
        finally:
            self._db.close_session(session)

    def renovar_token(self, token_antigo: str) -> Optional[str]:
        """
        Renova um token existente.
        """
        from helpers.jwt_helper import JWTHelper

        session: Session = self._db.get_session()
        try:
            token_db = session.query(TokenSessao).filter_by(
                token=token_antigo,
                ativo=True
            ).first()

            if not token_db:
                return None

            # Gera novo token JWT
            novo_token = JWTHelper.renovar_token(token_antigo)
            if not novo_token:
                return None

            # Desativa token antigo
            token_db.ativo = False

            # Calcula validade do novo token (mesma do antigo)
            if token_db.dt_expiracao:
                validade_restante = token_db.dt_expiracao - self._timestamp_atual()
                minutos_validade = max(60, validade_restante // 60)
            else:
                minutos_validade = JWTHelper.ACCESS_TOKEN_EXPIRE_MINUTES

            # Cria novo token no banco
            novo_token_db = TokenSessao(
                id_usuario=token_db.id_usuario,
                token=novo_token,
                dt_criacao=self._timestamp_atual(),
                dt_expiracao=self._timestamp_atual() + (minutos_validade * 60),
                dt_ultimo_acesso=self._timestamp_atual(),
                ativo=True
            )
            session.add(novo_token_db)
            session.commit()

            return novo_token

        except Exception as e:
            session.rollback()
            print(f"Erro ao renovar token: {e}")
            return None
        finally:
            self._db.close_session(session)

    def atualizar_ultimo_acesso(self, token: str) -> bool:
        """Atualiza o timestamp do último acesso do token"""
        session: Session = self._db.get_session()
        try:
            session.query(TokenSessao).filter_by(
                token=token,
                ativo=True
            ).update({"dt_ultimo_acesso": self._timestamp_atual()})
            session.commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar acesso: {e}")
            return False
        finally:
            self._db.close_session(session)

    def listar_todos_tokens(self) -> list:
        """Busca todos os tokens para análise de acesso"""
        session: Session = self._db.get_session()
        try:
            return session.query(TokenSessao).all()
        except Exception as e:
            print(f"Erro ao listar tokens: {e}")
            return []
        finally:
            self._db.close_session(session)
    def reativar_token(self, id_usuario: int) -> Optional[str]:
        """Reativa o último token do usuário"""
        session: Session = self._db.get_session()
        try:
            # Buscar último token (mesmo que inativo)
            token_db = session.query(TokenSessao).filter_by(
                id_usuario=id_usuario
            ).order_by(TokenSessao.dt_criacao.desc()).first()

            if token_db:
                # Reativar token existente
                token_db.ativo = True
                token_db.dt_ultimo_acesso = self._timestamp_atual()
                # Renovar expiração (mais 60 minutos)
                token_db.dt_expiracao = self._timestamp_atual() + (60 * 60)
                session.commit()
                return token_db.token

            return None
        except Exception as e:
            print(f"Erro ao reativar token: {e}")
            return None
        finally:
            self._db.close_session(session)