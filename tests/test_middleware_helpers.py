"""Testes de middleware e helpers."""
from io import BytesIO
from datetime import datetime

import pytest
import pandas as pd
import streamlit as st

from helpers import formata
from helpers.upload import UploadHelper
from middleware.access_control import AccessControlMiddleware
from middleware.auth import Auth
from model.TabUsuarios import Usuario


class _FakeLoginController:
    def __init__(self, db=None, admin=False, pages=None):
        self.db = db
        self._admin = admin
        self._pages = pages or []
        self.init_called = False

    def init_session(self):
        self.init_called = True

    def is_admin(self):
        return self._admin

    def get_menu_pages_for_logged_user(self):
        return self._pages


class _SessionDB:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return self.session


class _FakeUpload:
    def __init__(self, name, content):
        self.name = name
        self._content = content

    def getbuffer(self):
        return BytesIO(self._content).getbuffer()


class TestAccessControlMiddleware:
    def test_require_admin_reflete_login_controller(self):
        assert AccessControlMiddleware.require_admin(_FakeLoginController(admin=True)) is True
        assert AccessControlMiddleware.require_admin(_FakeLoginController(admin=False)) is False

    def test_get_allowed_pages_delega_para_login_controller(self):
        pages = [{"nome": "Dashboard"}]
        assert AccessControlMiddleware.get_allowed_pages(_FakeLoginController(pages=pages)) == pages


class TestAuthMiddleware:
    def test_require_login_retorna_true_para_sessao_logada(self, mock_streamlit_session, monkeypatch):
        mock_streamlit_session["logged_in"] = True
        mock_streamlit_session["auth_token"] = "token-ok"

        chamadas = []

        class _FakeTokenController:
            def atualizar_ultimo_acesso(self, token):
                chamadas.append(token)

        monkeypatch.setattr("middleware.auth.TokenController", lambda: _FakeTokenController())

        login_controller = _FakeLoginController()
        assert Auth.require_login(login_controller) is True
        assert chamadas == ["token-ok"]
        assert login_controller.init_called is True

    def test_require_login_hidrata_sessao_por_token_valido(self, temp_db, mock_streamlit_session, monkeypatch):
        usuario = Usuario(
            email="auth@teste.com",
            senha="hash",
            nome="Auth User",
            perfil="Admin",
            situacao="Ativado",
            id_empresa=1,
        )
        temp_db.add(usuario)
        temp_db.commit()

        mock_streamlit_session["auth_token"] = "jwt-ok"
        login_controller = _FakeLoginController(db=_SessionDB(temp_db))

        chamadas = []

        class _FakeTokenController:
            def atualizar_ultimo_acesso(self, token):
                chamadas.append(token)

        monkeypatch.setattr("middleware.auth.TokenController", lambda: _FakeTokenController())
        monkeypatch.setattr("middleware.auth.JWTHelper.verificar_token", lambda token: {"id_usuario": usuario.id_usuario})

        assert Auth.require_login(login_controller) is True
        assert st.session_state["logged_in"] is True
        assert st.session_state["id_usuario"] == usuario.id_usuario
        assert st.session_state["perfil"] == "Admin"
        assert chamadas == ["jwt-ok"]


class TestFormataHelper:
    def test_formata_data_e_numeros(self):
        assert formata.data_br("2024-12-15") == "15/12/2024"
        assert formata.data_us("15/12/2024") == "2024-12-15"
        assert formata.formatar_numero(1234.56) == "1.234,56"
        assert formata.reais(1234.56) == "R$ 1.234,56"
        assert formata.porcentagem(0.157, 1) == "15,7%"
        assert formata.zero(7, 3) == "007"

    def test_formatar_numero_e_reais_com_texto_monetario(self):
        assert formata.formatar_numero("R$ 1.234,56") == "1.234,56"
        assert formata.reais("R$ 1.234,56") == "R$ 1.234,56"

    def test_conversor_seguro_para_float(self):
        assert formata.converter_para_float_seguro("R$ 1.234,56") == 1234.56
        assert formata.converter_para_float_seguro("-10,00") == -10.0
        assert formata.converter_para_float_seguro("(10,00)") == -10.0
        assert formata.converter_para_float_seguro(None) == 0.0

    def test_formatar_numero_preserva_valor_negativo(self):
        assert formata.formatar_numero(-10) == "-10,00"
        assert formata.decimal(-10) == "-10,00"
        assert formata.reais(-10) == "R$ -10,00"

    def test_normalizar_coluna_data(self):
        resultado = formata.normalizar_coluna_data(pd.Series(["2024-12-25", "invalid"]))
        assert resultado.iloc[0].strftime("%Y-%m-%d") == "2024-12-25"
        assert resultado.iloc[1].date() == datetime.now().date()

    def test_reais_com_texto_formatado(self):
        assert formata.reais("R$ 1.234,56") == "R$ 1.234,56"
        assert formata.reais("R$ 1.234,56", simbolo=False) == "1.234,56"

    def test_formata_texto_e_documentos(self):
        assert formata.limpar("Olá!!! Mundo!!!") == "Olá Mundo"
        assert formata.nome_proprio("joão da silva") == "João da Silva"
        assert formata.cnpj("12345678000199") == "12.345.678/0001-99"
        assert formata.cpf("12345678900") == "123.456.789-00"
        assert formata.telefone("11912345678") == "(11) 91234-5678"
        assert formata.cep("12345678") == "12345-678"


class TestUploadHelper:
    def test_salvar_obter_e_excluir_imagem(self, tmp_path, monkeypatch):
        monkeypatch.setattr(UploadHelper, "BASE_DIR", tmp_path)
        monkeypatch.setattr(UploadHelper, "UPLOAD_DIR", tmp_path / "views" / "uploads" / "logo")

        arquivo = _FakeUpload("logo.png", b"conteudo-imagem")

        caminho_relativo = UploadHelper.salvar_imagem(arquivo, 99)

        assert caminho_relativo is not None
        assert UploadHelper.obter_url_imagem(caminho_relativo) == caminho_relativo
        assert UploadHelper.excluir_imagem(caminho_relativo) is True
        assert UploadHelper.obter_url_imagem(caminho_relativo) == ""