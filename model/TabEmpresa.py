from sqlalchemy import Column, Integer, String, Boolean, Text
from model.TabUsuarios import Base


class TabEmpresa(Base):
    __tablename__ = "Tabcad_empresas"

    id_empresa = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(200), nullable=False, default="Minha Empresa")
    cnpj = Column(String(18), unique=True, nullable=True)
    razao_social = Column(String(200), nullable=True)
    email = Column(String(200), nullable=True)
    telefone = Column(String(20), nullable=True)
    endereco = Column(String(500), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(2), nullable=True)
    cep = Column(String(10), nullable=True)

    # Personalização
    logo = Column(Text, nullable=True)
    tema_primario = Column(String(20), default="#1f2937")
    tema_secundario = Column(String(20), default="#2563eb")
    sidebar_fundo = Column(String(20), default="#fafafa")
    sidebar_texto = Column(String(20), default="#1f2937")

    # Status
    ativo = Column(Boolean, default=True)
    dt_criacao = Column(Integer)
    dt_atualizacao = Column(Integer)
    cor_alerta_vermelho = Column(String(20), default="#dc2626")
    cor_alerta_amarelo = Column(String(20), default="#2563eb")
    cor_alerta_verde = Column(String(20), default="#059669")
    def __repr__(self):
        return f"<TabEmpresa(id={self.id_empresa}, nome={self.nome})>"