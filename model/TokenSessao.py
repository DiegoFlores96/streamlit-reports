from sqlalchemy import Column, Integer, String, Boolean
from model.TabUsuarios import Base


class TokenSessao(Base):
    __tablename__ = "Tabcad_token_sessao"

    id_token = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, nullable=False)
    token = Column(String(512), nullable=False, unique=True)
    dt_criacao = Column(Integer, nullable=False)
    dt_expiracao = Column(Integer, nullable=True)
    dt_ultimo_acesso = Column(Integer, nullable=True)
    ativo = Column(Boolean, default=True)

    def __repr__(self):
        return f"<TokenSessao(id_token={self.id_token}, id_usuario={self.id_usuario}, ativo={self.ativo})>"