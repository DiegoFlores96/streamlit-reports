from sqlalchemy import Column, ForeignKey, Integer

from model.TabUsuarios import Base


class UsuarioDashboardAcesso(Base):
    __tablename__ = "Tabrel_usuario_dashboard"

    id_acesso = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("Tabcad_usuarios.id_usuario"), nullable=False)
    id_dashboard = Column(Integer, ForeignKey("Tabcad_dashboards.id_dashboard"), nullable=False)