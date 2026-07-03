"""Controlador de gerenciamento de empresas.

Responsável por:
  - CRUD de empresas (criar, listar, atualizar, deletar)
  - Gerenciamento de dados da empresa (nome, CNPJ, contato, etc)
  - Temas e configurações visuais
  - Associação de usuários a empresas
  - Validação de dados da empresa
"""
import logging
import streamlit as st
from datetime import datetime
from db.conexao import Conexao
from model.TabEmpresa import TabEmpresa
from model.TabUsuarios import Usuario
from typing import Optional, Dict, Any, List
import base64
from helpers.upload import UploadHelper
from helpers.validators import cnpj_valido, nome_valido

# Configurar logger
logger = logging.getLogger(__name__)


class EmpresaController:
    # Campos permitidos para edição
    CAMPOS_EDITAVEIS = {
        'nome', 'razao_social', 'email', 'telefone',
        'endereco', 'cidade', 'estado', 'cep',
        'tema_primario', 'tema_secundario', 'sidebar_fundo', 'sidebar_texto',
        'cor_alerta_vermelho', 'cor_alerta_amarelo', 'cor_alerta_verde', 'logo'
    }
    
    # Cores padrão para novas empresas
    CORES_PADRAO = {
        'tema_primario': "#1f2937",
        'tema_secundario': "#2563eb",
        'sidebar_fundo': "#fafafa",
        'sidebar_texto': "#1f2937",
        'cor_alerta_vermelho': "#dc2626",
        'cor_alerta_amarelo': "#1f2937",
        'cor_alerta_verde': "#059669"
    }
    
    # Valores padrão
    NOME_PADRAO = "Minha Empresa"
    STATUS_ATIVO = True

    def __init__(self):
        self.db = Conexao()

    @staticmethod
    def _timestamp():
        return int(datetime.now().timestamp())

    def get_empresas(self, ativas_apenas: bool = True) -> List[TabEmpresa]:
        """
        Busca empresas do banco de dados.
        
        Args:
            ativas_apenas: Se True, retorna apenas empresas ativas. Se False, todas.
            
        Returns:
            Lista de empresas ordenadas por nome
        """
        session = self.db.get_session()
        try:
            query = session.query(TabEmpresa)
            if ativas_apenas:
                query = query.filter_by(ativo=True)
            return query.order_by(TabEmpresa.nome).all()
        except Exception as e:
            logger.error(f"Erro ao listar empresas", exc_info=True)
            return []
        finally:
            self.db.close_session(session)

    def listar_empresas(self) -> List[TabEmpresa]:
        """[DEPRECADO] Use get_empresas() - Mantido para backward compatibility"""
        return self.get_empresas(ativas_apenas=True)

    def listar_todas_empresas(self) -> List[TabEmpresa]:
        """[DEPRECADO] Use get_empresas(ativas_apenas=False) - Mantido para backward compatibility"""
        return self.get_empresas(ativas_apenas=False)

    def get_empresa_do_usuario(self, id_usuario: int) -> Optional[TabEmpresa]:
        """Busca a empresa do usuário logado (read-only).
        
        Nota: Não modifica o banco de dados. Se o usuário não tiver empresa
        associada, retorna a primeira empresa ativa disponível (mas sem atualizar o banco).
        """
        session = self.db.get_session()
        try:
            usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
            if usuario and usuario.id_empresa:
                return session.query(TabEmpresa).filter_by(id_empresa=usuario.id_empresa).first()

            # Retorna primeira empresa ativa disponível (sem commit)
            return session.query(TabEmpresa).filter_by(ativo=True).first()
        except Exception as e:
            logger.error(f"Erro ao buscar empresa com id {id_empresa}", exc_info=True)
            return None
        finally:
            self.db.close_session(session)

    def get_empresa_por_id(self, id_empresa: int) -> Optional[TabEmpresa]:
        """Busca empresa por ID"""
        session = self.db.get_session()
        try:
            return session.query(TabEmpresa).filter_by(id_empresa=id_empresa).first()
        finally:
            self.db.close_session(session)

    def get_todas_empresas(self) -> List[TabEmpresa]:
        """[DEPRECADO] Use get_empresas(ativas_apenas=False) - Mantido para backward compatibility"""
        return self.get_empresas(ativas_apenas=False)

    def atualizar_empresa(self, id_empresa: int, dados: Dict[str, Any]) -> tuple[bool, str]:
        """Atualiza dados da empresa com whitelist de campos permitidos.
        
        Args:
            id_empresa: ID da empresa a atualizar
            dados: Dicionário com dados a atualizar (apenas campos permitidos serão atualizados)
            
        Returns:
            (sucesso, mensagem)
        """
        session = self.db.get_session()
        try:
            empresa = session.query(TabEmpresa).filter_by(id_empresa=id_empresa).first()
            if not empresa:
                return False, "Empresa não encontrada"

            # Aplicar whitelist - apenas campos permitidos serão atualizados
            for key, value in dados.items():
                if key not in self.CAMPOS_EDITAVEIS:
                    continue  # Ignorar campos não permitidos
                if hasattr(empresa, key) and value is not None:
                    setattr(empresa, key, value)

            empresa.dt_atualizacao = self._timestamp()
            session.commit()
            return True, "Configurações salvas com sucesso!"
        except Exception as e:
            session.rollback()
            return False, f"Erro ao salvar: {str(e)}"
        finally:
            self.db.close_session(session)

    def upload_logo(self, arquivo, id_empresa: int) -> Optional[str]:
        """Faz upload da logo e salva como arquivo"""
        # Salvar arquivo e obter caminho
        caminho = UploadHelper.salvar_imagem(arquivo, id_empresa)

        if caminho:
            # Salvar apenas o caminho no banco
            self.atualizar_empresa(id_empresa, {'logo': caminho})
            return caminho

        return None

    def criar_empresa_padrao(self, id_usuario: int) -> bool:
        """Cria uma empresa padrão se não existir.
        
        Args:
            id_usuario: ID do usuário para associar à empresa
            
        Returns:
            True se empresa foi criada ou já existia
        """
        session = self.db.get_session()
        try:
            empresa = session.query(TabEmpresa).first()
            if empresa:
                return True

            timestamp = self._timestamp()
            nova_empresa = TabEmpresa(
                nome=self.NOME_PADRAO,
                cnpj=None,
                tema_primario=self.CORES_PADRAO['tema_primario'],
                tema_secundario=self.CORES_PADRAO['tema_secundario'],
                sidebar_fundo=self.CORES_PADRAO['sidebar_fundo'],
                sidebar_texto=self.CORES_PADRAO['sidebar_texto'],
                ativo=self.STATUS_ATIVO,
                dt_criacao=timestamp,
                dt_atualizacao=timestamp,
                cor_alerta_vermelho=self.CORES_PADRAO['cor_alerta_vermelho'],
                cor_alerta_amarelo=self.CORES_PADRAO['cor_alerta_amarelo'],
                cor_alerta_verde=self.CORES_PADRAO['cor_alerta_verde']
            )
            session.add(nova_empresa)
            session.commit()

            usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
            if usuario:
                usuario.id_empresa = nova_empresa.id_empresa
                session.commit()

            return True
        except Exception as e:
            logger.error(f"Erro ao criar empresa padrão para usuário {id_usuario}", exc_info=True)
            return False
        finally:
            self.db.close_session(session)

    def criar_empresa_completa(self, dados: Dict[str, Any], id_usuario: int) -> tuple[bool, str, Optional[int]]:
        """Cria uma nova empresa com os dados fornecidos"""
        session = self.db.get_session()
        try:
            # Validar nome
            nome = dados.get('nome', '').strip()
            nome_ok, nome_err = nome_valido(nome)
            if not nome_ok:
                return False, nome_err, None
            
            # Tratar CNPJ vazio como None
            cnpj = dados.get('cnpj', '').strip()
            if cnpj == '':
                cnpj = None

            # Validar CNPJ se fornecido
            if cnpj:
                cnpj_ok, cnpj_err = cnpj_valido(cnpj)
                if not cnpj_ok:
                    return False, cnpj_err, None
                # Verificar duplicata
                existe = session.query(TabEmpresa).filter_by(cnpj=cnpj).first()
                if existe:
                    return False, "CNPJ já cadastrado", None

            timestamp = self._timestamp()
            nova_empresa = TabEmpresa(
                nome=dados['nome'],
                cnpj=cnpj,
                razao_social=dados.get('razao_social', ''),
                email=dados.get('email', ''),
                telefone=dados.get('telefone', ''),
                endereco=dados.get('endereco', ''),
                cidade=dados.get('cidade', ''),
                estado=dados.get('estado', ''),
                cep=dados.get('cep', ''),
                ativo=True,
                dt_criacao=timestamp,
                dt_atualizacao=timestamp,
                cor_alerta_vermelho=dados.get('cor_alerta_vermelho', '#dc2626'),
                cor_alerta_amarelo=dados.get('cor_alerta_amarelo', '#1f2937'),
                cor_alerta_verde=dados.get('cor_alerta_verde', '#059669')
            )
            session.add(nova_empresa)
            session.commit()

            # Associar ao usuário atual
            usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
            if usuario:
                usuario.id_empresa = nova_empresa.id_empresa
                session.commit()

            return True, "Empresa cadastrada com sucesso!", nova_empresa.id_empresa
        except Exception as e:
            session.rollback()
            return False, f"Erro ao criar empresa: {str(e)}", None
        finally:
            self.db.close_session(session)

    def excluir_empresa(self, id_empresa: int) -> tuple[bool, str]:
        """Desativa uma empresa"""
        session = self.db.get_session()
        try:
            empresa = session.query(TabEmpresa).filter_by(id_empresa=id_empresa).first()
            if not empresa:
                return False, "Empresa não encontrada"

            empresa.ativo = False
            empresa.dt_atualizacao = self._timestamp()
            session.commit()
            return True, f"Empresa {empresa.nome} desativada com sucesso"
        except Exception as e:
            session.rollback()
            return False, f"Erro ao desativar empresa: {str(e)}"
        finally:
            self.db.close_session(session)

    def reativar_empresa(self, id_empresa: int) -> tuple[bool, str]:
        """Reativa uma empresa"""
        session = self.db.get_session()
        try:
            empresa = session.query(TabEmpresa).filter_by(id_empresa=id_empresa).first()
            if not empresa:
                return False, "Empresa não encontrada"

            empresa.ativo = True
            empresa.dt_atualizacao = self._timestamp()
            session.commit()
            return True, f"Empresa {empresa.nome} reativada com sucesso"
        except Exception as e:
            session.rollback()
            return False, f"Erro ao reativar empresa: {str(e)}"
        finally:
            self.db.close_session(session)

    def associar_usuarios_empresa(self, ids_usuarios: List[int], id_empresa: int) -> tuple[bool, str]:
        """Associa uma lista de usuários a uma empresa"""
        session = self.db.get_session()
        try:
            empresa = session.query(TabEmpresa).filter_by(id_empresa=id_empresa).first()
            if not empresa:
                return False, "Empresa não encontrada"

            associados = 0
            for id_usuario in ids_usuarios:
                usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
                if usuario:
                    usuario.id_empresa = id_empresa
                    associados += 1

            session.commit()
            return True, f"{associados} usuário(s) associado(s) à empresa {empresa.nome}"
        except Exception as e:
            session.rollback()
            return False, f"Erro ao associar: {str(e)}"
        finally:
            self.db.close_session(session)

    def listar_usuarios_por_empresa(self, id_empresa: int) -> List[Usuario]:
        """Lista usuários de uma empresa"""
        session = self.db.get_session()
        try:
            return session.query(Usuario).filter_by(id_empresa=id_empresa).all()
        finally:
            self.db.close_session(session)

    def get_empresa_colors(self, id_empresa: int) -> Dict[str, str]:
        """Busca as cores de identidade visual e alertas da empresa por ID"""
        session = self.db.get_session()
        try:
            empresa = session.query(TabEmpresa).filter_by(id_empresa=id_empresa).first()
            if empresa:
                return {
                    "tema_primario": empresa.tema_primario or "#1f2937",
                    "tema_secundario": empresa.tema_secundario or "#2563eb",
                    "sidebar_fundo": empresa.sidebar_fundo or "#fafafa",
                    "sidebar_texto": empresa.sidebar_texto or "#1f2937",
                    "cor_alerta_vermelho": empresa.cor_alerta_vermelho or "#1f2937",
                    "cor_alerta_amarelo": empresa.cor_alerta_amarelo or "#1f2937",
                    "cor_alerta_verde": empresa.cor_alerta_verde or "#1f2937"
                }

            # Caso não encontre a empresa, retorna um dicionário com cores padrão (fallback)
            return {
                "tema_primario": "#1f2937",
                "tema_secundario": "#2563eb",
                "sidebar_fundo": "#fafafa",
                "sidebar_texto": "#1f2937",
                "cor_alerta_vermelho": "#1f2937",
                "cor_alerta_amarelo": "#1f2937",
                "cor_alerta_verde": "#1f2937"
            }
        except Exception as e:
            logger.warning(f"Usando cores padrão (erro ao buscar cores personalizadas)", exc_info=False)
            # Retorno seguro em caso de falha na conexão com o banco
            return {
                "tema_primario": "#1f2937",
                "tema_secundario": "#2563eb",
                "sidebar_fundo": "#fafafa",
                "sidebar_texto": "#1f2937",
                "cor_alerta_vermelho": "#1f2937",
                "cor_alerta_amarelo": "#1f2937",
                "cor_alerta_verde": "#1f2937"
            }
        finally:
            self.db.close_session(session)



# Garantir que a classe seja exportada
__all__ = ['EmpresaController']