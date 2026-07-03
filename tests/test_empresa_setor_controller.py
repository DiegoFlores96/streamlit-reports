"""Testes para Controllers - EmpresaController e SetorController."""
import pytest
import time
from controller.empresaController import EmpresaController
from controller.setorController import SetorController
from model.TabEmpresa import TabEmpresa
from model.SetorDashboard import SetorDashboard


class TestEmpresaController:
    """Testes para EmpresaController."""

    def test_listar_empresas_ativas(self, temp_db):
        """Testa listagem de empresas ativas."""
        timestamp = int(time.time())
        
        # Cria empresas
        empresa1 = TabEmpresa(
            nome="Empresa Ativa 1",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        empresa2 = TabEmpresa(
            nome="Empresa Ativa 2",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        empresa3 = TabEmpresa(
            nome="Empresa Inativa",
            ativo=False,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        
        temp_db.add_all([empresa1, empresa2, empresa3])
        temp_db.commit()
        
        # Lista apenas ativas
        ativas = temp_db.query(TabEmpresa).filter_by(ativo=True).all()
        assert len(ativas) >= 2
        
        inativas = temp_db.query(TabEmpresa).filter_by(ativo=False).all()
        assert any(e.nome == "Empresa Inativa" for e in inativas)

    def test_get_empresa_por_id(self, temp_db):
        """Testa busca de empresa por ID."""
        timestamp = int(time.time())
        
        empresa = TabEmpresa(
            nome="Empresa Teste",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        temp_db.add(empresa)
        temp_db.commit()
        
        # Busca por ID
        empresa_encontrada = temp_db.query(TabEmpresa).filter_by(id_empresa=empresa.id_empresa).first()
        assert empresa_encontrada is not None
        assert empresa_encontrada.nome == "Empresa Teste"

    def test_atualizar_cores_empresa(self, temp_db):
        """Testa atualização de cores da empresa."""
        timestamp = int(time.time())
        
        empresa = TabEmpresa(
            nome="Empresa Cores",
            tema_primario="#1f2937",
            tema_secundario="#2563eb",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        temp_db.add(empresa)
        temp_db.commit()
        
        # Atualiza cores
        empresa.tema_primario = "#ff0000"
        empresa.tema_secundario = "#00ff00"
        empresa.dt_atualizacao = int(time.time())
        temp_db.commit()
        
        # Verifica
        empresa_check = temp_db.query(TabEmpresa).filter_by(id_empresa=empresa.id_empresa).first()
        assert empresa_check.tema_primario == "#ff0000"
        assert empresa_check.tema_secundario == "#00ff00"

    def test_empresa_com_logo(self, temp_db):
        """Testa armazenamento de logo em base64."""
        timestamp = int(time.time())
        
        logo_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        empresa = TabEmpresa(
            nome="Empresa Com Logo",
            logo=logo_base64,
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        temp_db.add(empresa)
        temp_db.commit()
        
        # Verifica
        empresa_check = temp_db.query(TabEmpresa).filter_by(id_empresa=empresa.id_empresa).first()
        assert empresa_check.logo == logo_base64
        assert "base64" in empresa_check.logo

    def test_cores_alerta_empresa(self, temp_db):
        """Testa cores de alerta padrão."""
        timestamp = int(time.time())
        
        empresa = TabEmpresa(
            nome="Empresa Alerta",
            ativo=True,
            dt_criacao=timestamp,
            dt_atualizacao=timestamp
        )
        temp_db.add(empresa)
        temp_db.commit()
        
        # Verifica cores padrão
        empresa_check = temp_db.query(TabEmpresa).filter_by(id_empresa=empresa.id_empresa).first()
        assert empresa_check.cor_alerta_vermelho == "#dc2626"
        assert empresa_check.cor_alerta_amarelo == "#2563eb"
        assert empresa_check.cor_alerta_verde == "#059669"


class TestSetorController:
    """Testes para SetorController."""

    def test_listar_setores(self, temp_db):
        """Testa listagem de setores."""
        # Cria setores
        setor1 = SetorDashboard(nome_setor="Vendas", situacao="Ativado")
        setor2 = SetorDashboard(nome_setor="Financeiro", situacao="Ativado")
        
        temp_db.add_all([setor1, setor2])
        temp_db.commit()
        
        # Lista
        setores = temp_db.query(SetorDashboard).all()
        assert len(setores) >= 2
        nomes = [s.nome_setor for s in setores]
        assert "Vendas" in nomes
        assert "Financeiro" in nomes

    def test_buscar_setor_por_nome(self, temp_db):
        """Testa busca de setor por nome."""
        setor = SetorDashboard(nome_setor="Estoque", situacao="Ativado")
        temp_db.add(setor)
        temp_db.commit()
        
        # Busca
        setor_found = temp_db.query(SetorDashboard).filter_by(nome_setor="Estoque").first()
        assert setor_found is not None
        assert setor_found.situacao == "Ativado"

    def test_setor_unico(self, temp_db):
        """Testa que nomes de setores são únicos."""
        setor1 = SetorDashboard(nome_setor="RH", situacao="Ativado")
        temp_db.add(setor1)
        temp_db.commit()
        
        # Tenta criar outro com mesmo nome
        setor2 = SetorDashboard(nome_setor="RH", situacao="Ativado")
        temp_db.add(setor2)
        
        # Deve falhar por constraint UNIQUE
        with pytest.raises(Exception):
            temp_db.commit()
