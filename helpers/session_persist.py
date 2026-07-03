"""Módulo para persistência de sessão."""
import streamlit as st
from typing import Optional


class SessionPersist:
    """Gerencia persistência de sessão."""

    TOKEN_KEY: str = 'auth_token'

    @classmethod
    def salvar_token(cls, token: str) -> None:
        """Salva token na sessão e na URL."""
        st.session_state[cls.TOKEN_KEY] = token
        # Adicionar token na URL
        st.query_params['token'] = token
        st.rerun()

    @classmethod
    def remover_token(cls) -> None:
        """Remove token."""
        if cls.TOKEN_KEY in st.session_state:
            del st.session_state[cls.TOKEN_KEY]
        if 'token' in st.query_params:
            del st.query_params['token']
        st.rerun()

    @classmethod
    def recuperar_token(cls) -> Optional[str]:
        """Recupera token da sessão ou URL."""
        # Primeiro da sessão
        token = st.session_state.get(cls.TOKEN_KEY)
        if token:
            return token

        # Depois da URL
        token = st.query_params.get('token')
        if token:
            st.session_state[cls.TOKEN_KEY] = token
            return token

        return None