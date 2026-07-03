from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Usuario(Base):
    __tablename__ = "Tabcad_usuarios"

    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha = Column(String(255), nullable=False)
    nome = Column(String(255), nullable=False)
    perfil = Column(String(20), default="Padrao")
    situacao = Column(String(50), default='Ativado')
    dt_criacao = Column(Integer)
    dt_ultima_atualizacao = Column("dt_utima_atualizacao", Integer)
    dt_desativacao = Column(Integer, nullable=True)
    id_empresa = Column(Integer, ForeignKey("Tabcad_empresas.id_empresa"), nullable=True)

    @property
    def dt_utima_atualizacao(self):
        return self.dt_ultima_atualizacao

    @dt_utima_atualizacao.setter
    def dt_utima_atualizacao(self, value):
        self.dt_ultima_atualizacao = value

    def __repr__(self):
        return f"<Usuario(id_usuario={self.id_usuario}, email={self.email}, nome={self.nome}, situacao={self.situacao})>"