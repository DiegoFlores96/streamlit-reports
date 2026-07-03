from db.conexao import Conexao
from model.SetorDashboard import SetorDashboard
from sqlalchemy import func


class SetorController:
    def __init__(self):
        self.db = Conexao()

    def list_setores(self) -> list[SetorDashboard]:
        session = self.db.get_session()
        try:
            return session.query(SetorDashboard).order_by(SetorDashboard.nome_setor).all()
        finally:
            self.db.close_session(session)

    def create_setor(self, nome_setor: str) -> tuple[bool, str]:
        nome_setor = (nome_setor or "").strip()
        if not nome_setor:
            return False, "Informe o nome do setor."

        session = self.db.get_session()
        try:
            # Validar case-insensitively - impedir VENDAS e vendas serem diferentes
            exists = session.query(SetorDashboard).filter(
                func.lower(SetorDashboard.nome_setor) == nome_setor.lower()
            ).first()
            if exists:
                return False, "Setor já existe (validação case-insensitive)."

            setor = SetorDashboard(nome_setor=nome_setor, situacao="Ativado")
            session.add(setor)
            session.commit()
            return True, "Setor criado com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao criar setor: {str(e)}"
        finally:
            self.db.close_session(session)

    def update_setor(self, id_setor: int, nome_setor: str, situacao: str) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            setor = session.query(SetorDashboard).filter_by(id_setor=id_setor).first()
            if not setor:
                return False, "Setor não encontrado."

            nome_setor_clean = (nome_setor or "").strip()
            
            # Validar se novo nome já existe em outro setor (case-insensitive)
            if nome_setor_clean and nome_setor_clean.lower() != setor.nome_setor.lower():
                duplicate = session.query(SetorDashboard).filter(
                    func.lower(SetorDashboard.nome_setor) == nome_setor_clean.lower(),
                    SetorDashboard.id_setor != id_setor
                ).first()
                if duplicate:
                    return False, "Setor com este nome já existe."
            
            setor.nome_setor = nome_setor_clean
            setor.situacao = (situacao or "Ativado").strip().title()
            session.commit()
            return True, "Setor atualizado com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao atualizar setor: {str(e)}"
        finally:
            self.db.close_session(session)

    def deactivate_setor(self, id_setor: int) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            setor = session.query(SetorDashboard).filter_by(id_setor=id_setor).first()
            if not setor:
                return False, "Setor não encontrado."

            setor.situacao = "Desativado"
            session.commit()
            return True, "Setor desativado com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao desativar setor: {str(e)}"
        finally:
            self.db.close_session(session)