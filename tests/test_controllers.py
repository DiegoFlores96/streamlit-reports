"""Testes de controllers."""
from pathlib import Path

import pytest

from controller.dashboardController import DashboardController
from controller.empresaController import EmpresaController
from controller.setorController import SetorController
from model.DashboardItem import DashboardItem
from model.SetorDashboard import SetorDashboard
from model.TabEmpresa import TabEmpresa
from model.TabUsuarios import Usuario


class _SessionDB:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return self.session

    def close_session(self, _session):
        return None


@pytest.fixture
def controller_session(temp_db):
    return temp_db


class TestEmpresaController:
    def test_listar_empresas_retorna_apenas_ativas(self, controller_session):
        controller = EmpresaController()
        controller.db = _SessionDB(controller_session)

        controller_session.add(
            TabEmpresa(nome="Inativa", cnpj="11.111.111/0001-11", ativo=False)
        )
        controller_session.commit()

        empresas = controller.listar_empresas()

        assert all(empresa.ativo for empresa in empresas)
        assert any(empresa.nome == "Empresa Teste" for empresa in empresas)

    def test_get_empresa_do_usuario_associa_empresa_ativa(self, controller_session):
        controller = EmpresaController()
        controller.db = _SessionDB(controller_session)

        usuario = Usuario(
            email="semempresa@teste.com",
            senha="hash",
            nome="Usuario Sem Empresa",
            perfil="Padrao",
            situacao="Ativado",
        )
        controller_session.add(usuario)
        controller_session.commit()

        empresa = controller.get_empresa_do_usuario(usuario.id_usuario)

        # Método get_empresa_do_usuario agora é read-only
        # Retorna a primeira empresa ativa disponível, mas sem modificar o banco
        assert empresa is not None
        assert empresa.ativo is True

    def test_criar_empresa_completa_sucesso(self, controller_session):
        controller = EmpresaController()
        controller.db = _SessionDB(controller_session)

        usuario = Usuario(
            email="empresa.controller@teste.com",
            senha="hash",
            nome="Usuario Empresa",
            perfil="Admin",
            situacao="Ativado",
        )
        controller_session.add(usuario)
        controller_session.commit()

        ok, mensagem, id_empresa = controller.criar_empresa_completa(
            {
                "nome": "Nova Empresa",
                "cnpj": "22.222.222/0001-22",
                "cor_alerta_vermelho": "#ff0000",
            },
            usuario.id_usuario,
        )

        usuario_db = controller_session.query(Usuario).filter_by(id_usuario=usuario.id_usuario).first()
        empresa_db = controller_session.query(TabEmpresa).filter_by(id_empresa=id_empresa).first()

        assert ok is True
        assert "sucesso" in mensagem.lower()
        assert id_empresa is not None
        assert empresa_db is not None
        assert empresa_db.cor_alerta_vermelho == "#ff0000"
        assert usuario_db.id_empresa == id_empresa

    def test_criar_empresa_completa_rejeita_cnpj_duplicado(self, controller_session):
        controller = EmpresaController()
        controller.db = _SessionDB(controller_session)

        usuario = Usuario(
            email="dup@teste.com",
            senha="hash",
            nome="Usuario Dup",
            perfil="Admin",
            situacao="Ativado",
        )
        controller_session.add(usuario)
        controller_session.commit()

        existente = controller_session.query(TabEmpresa).first()
        existente.cnpj = "33.333.333/0001-33"
        controller_session.commit()

        ok, mensagem, id_empresa = controller.criar_empresa_completa(
            {"nome": "Empresa Duplicada", "cnpj": "33.333.333/0001-33"},
            usuario.id_usuario,
        )

        assert ok is False
        assert "cnpj" in mensagem.lower()
        assert id_empresa is None


class TestSetorController:
    def test_create_update_deactivate_setor(self, controller_session):
        controller = SetorController()
        controller.db = _SessionDB(controller_session)

        ok, _ = controller.create_setor("Financeiro")
        setor = controller_session.query(SetorDashboard).filter_by(nome_setor="Financeiro").first()
        ok_update, _ = controller.update_setor(setor.id_setor, "Financeiro Novo", "desativado")
        controller_session.refresh(setor)
        ok_deactivate, _ = controller.deactivate_setor(setor.id_setor)
        controller_session.refresh(setor)

        assert ok is True
        assert ok_update is True
        assert setor.nome_setor == "Financeiro Novo"
        assert ok_deactivate is True
        assert setor.situacao == "Desativado"

    def test_create_setor_rejeita_duplicado(self, controller_session):
        controller = SetorController()
        controller.db = _SessionDB(controller_session)

        controller.create_setor("Operacoes")
        ok, mensagem = controller.create_setor("Operacoes")

        assert ok is False
        assert "já existe" in mensagem.lower()


class TestDashboardController:
    def test_obtener_arquivos_disponiveis_mapeia_raiz_e_subpasta(self, tmp_path):
        base = tmp_path / "dashboard"
        base.mkdir()
        (base / "indicadores.py").write_text("def render_page():\n    return None\n", encoding="utf-8")
        (base / "home.py").write_text("pass\n", encoding="utf-8")
        subpasta = base / "Financeiro"
        subpasta.mkdir()
        (subpasta / "DRE.py").write_text("def render_page():\n    return None\n", encoding="utf-8")

        controller = DashboardController()
        controller.caminho_base_dashboards = base

        arquivos = controller.obtener_arquivos_disponiveis()
        caminhos = [item["caminho_final"] for item in arquivos]

        assert "indicadores" in caminhos
        assert "financeiro/dre" in caminhos
        assert "home" not in caminhos

    def test_sincronizar_arquivos_fisicos_cria_setor_e_dashboards(self, controller_session, tmp_path):
        base = tmp_path / "dashboard"
        base.mkdir()
        (base / "geral.py").write_text("def render_page():\n    return None\n", encoding="utf-8")
        vendas = base / "Vendas"
        vendas.mkdir()
        (vendas / "painel.py").write_text("def render_page():\n    return None\n", encoding="utf-8")

        controller = DashboardController()
        controller.db = _SessionDB(controller_session)
        controller.caminho_base_dashboards = base

        ok, mensagem = controller.sincronizar_arquivos_fisicos()
        dashboards = controller_session.query(DashboardItem).all()
        setores = controller_session.query(SetorDashboard).all()

        assert ok is True
        assert "sincronização" in mensagem.lower()
        assert len(dashboards) == 2
        assert any(setor.nome_setor == "Geral" for setor in setores)
        assert any(dashboard.codigo_pagina == "vendas/painel" for dashboard in dashboards)