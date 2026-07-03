from sqlalchemy import Column, Integer, String

from model.TabUsuarios import Base


class SetorDashboard(Base):
    __tablename__ = "Tabcad_setor"

    id_setor = Column("id_setor", Integer, primary_key=True, autoincrement=True)
    nome_setor = Column("nome_setor", String(120), unique=True, nullable=False)
    situacao = Column(String(20), default="Ativado")