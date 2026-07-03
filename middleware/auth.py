import streamlit as st
from helpers.jwt_helper import JWTHelper
from controller.token_controller import TokenController


class Auth:
    @staticmethod
    def require_login(login_controller) -> bool:
        login_controller.init_session()

        # Já está logado? Atualiza o token
        if st.session_state.get('logged_in'):
            token = st.session_state.get('auth_token')
            if token:
                TokenController().atualizar_ultimo_acesso(token)
            return True

        # Verificar token na sessão
        token = st.session_state.get('auth_token')

        if token:
            payload = JWTHelper.verificar_token(token)
            if payload:
                session = login_controller.db.get_session()
                try:
                    from model.TabUsuarios import Usuario
                    usuario = session.query(Usuario).filter_by(
                        id_usuario=payload.get('id_usuario')
                    ).first()

                    if usuario and (usuario.situacao or "").lower() == "ativado":
                        st.session_state.logged_in = True
                        st.session_state.id_usuario = usuario.id_usuario
                        st.session_state.email = usuario.email
                        st.session_state.nome = usuario.nome
                        st.session_state.perfil = usuario.perfil or "Padrao"
                        # Atualizar acesso no banco
                        TokenController().atualizar_ultimo_acesso(token)
                        return True
                finally:
                    session.close()

        return False