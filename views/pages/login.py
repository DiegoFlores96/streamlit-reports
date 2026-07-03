import streamlit as st


def render_login_page(login_controller):
	st.title("Acesso")
	st.caption("Faça login para entrar ou crie um novo usuário.")

	tab_login, tab_register = st.tabs(["Entrar", "Criar usuário"])

	with tab_login:
		with st.form("login_form_main"):
			email = st.text_input("Email")
			senha = st.text_input("Senha", type="password")
			submit_login = st.form_submit_button("Entrar", use_container_width=True)

		if submit_login:
			ok, message = login_controller.login(email, senha)
			if ok:
				st.success(message)
				st.rerun()
			else:
				st.error(message)

	with tab_register:
		with st.form("register_form"):
			novo_email = st.text_input("Email")
			novo_nome = st.text_input("Nome completo")
			nova_senha = st.text_input("Senha", type="password")
			confirmar_senha = st.text_input("Confirmar senha", type="password")
			submit_register = st.form_submit_button("Criar usuário", use_container_width=True)

		if submit_register:
			if nova_senha != confirmar_senha:
				st.error("As senhas não conferem.")
			else:
				ok, message = login_controller.register_user(novo_email, nova_senha, novo_nome)
				if ok:
					st.success(message)
				else:
					st.error(message)
