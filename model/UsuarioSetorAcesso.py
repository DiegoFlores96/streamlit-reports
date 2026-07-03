from sqlalchemy import Column, ForeignKey, Integer

from model.TabUsuarios import Base


class UsuarioSetorAcesso(Base):
    __tablename__ = "Tabrel_usuario_setor"

    id_rel = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("Tabcad_usuarios.id_usuario"), nullable=False)
    id_setor = Column(Integer, ForeignKey("Tabcad_setor.id_setor"), nullable=False)