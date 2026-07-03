"""Smoke tests E2E-like e testes leves de performance/load."""
import time

import pytest

from controller.dashboardController import DashboardController
from controller.empresaController import EmpresaController
from controller.setorController import SetorController
from model.TabUsuarios import Usuario


class _SessionDB:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return self.session

    def close_session(self, _session):
        return None


@pytest.mark.integration
def test_auth_and_company_flow_smoke(temp_db):
    controller = EmpresaController()
    controller.db = _SessionDB(temp_db)

    usuario = Usuario(
        email="smoke@teste.com",
        senha="hash",
        nome="Smoke User",
        perfil="Admin",
        situacao="Ativado",
    )
    temp_db.add(usuario)
    temp_db.commit()

    ok, mensagem, id_empresa = controller.criar_empresa_completa(
        {"nome": "Empresa Smoke", "cnpj": "44.444.444/0001-44"},
        usuario.id_usuario,
    )

    empresa = controller.get_empresa_do_usuario(usuario.id_usuario)

    assert ok is True
    assert "sucesso" in mensagem.lower()
    assert id_empresa == empresa.id_empresa


@pytest.mark.slow
def test_setor_controller_bulk_create_load(temp_db):
    controller = SetorController()
    controller.db = _SessionDB(temp_db)

    inicio = time.perf_counter()
    for indice in range(100):
        ok, _ = controller.create_setor(f"Setor {indice}")
        assert ok is True
    duracao = time.perf_counter() - inicio

    assert duracao < 5
    assert len(controller.list_setores()) == 100


@pytest.mark.slow
def test_dashboard_file_scan_performance(tmp_path):
    base = tmp_path / "dashboard"
    base.mkdir()
    for indice in range(150):
        (base / f"pagina_{indice}.py").write_text("def render_page():\n    return None\n", encoding="utf-8")

    controller = DashboardController()
    controller.caminho_base_dashboards = base

    inicio = time.perf_counter()
    arquivos = controller.obtener_arquivos_disponiveis()
    duracao = time.perf_counter() - inicio

    assert len(arquivos) == 150
    assert duracao < 2