from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from model.TabUsuarios import Base


class DashboardItem(Base):
    __tablename__ = "Tabcad_dashboards"

    id_dashboard = Column(Integer, primary_key=True, autoincrement=True)
    nome_dashboard = Column(String(140), nullable=False)
    descricao = Column(String(255), default="")
    tipo_pagina = Column(String(20), default="dashboard")
    codigo_pagina = Column(String(60), default="dashboard_exemplo")
    id_setor = Column(Integer, ForeignKey("Tabcad_setor.id_setor"), nullable=False)
    ativo = Column(Boolean, default=True)

    setor = relationship("SetorDashboard")