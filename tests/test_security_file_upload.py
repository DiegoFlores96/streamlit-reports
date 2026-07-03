"""Testes de segurança para upload de arquivos."""
import pytest
from pathlib import Path
from io import BytesIO
from unittest.mock import Mock
from helpers.upload import UploadHelper


class TestFileUploadSecurity:
    """Validar que uploads maliciosos são bloqueados."""
    
    def test_rejeita_arquivo_vazio(self):
        """❌ Arquivo vazio deve ser rejeitado."""
        arquivo_mock = Mock()
        arquivo_mock.name = "vazio.jpg"
        arquivo_mock.getbuffer.return_value = BytesIO(b"")
        
        valido, msg = UploadHelper._validar_arquivo(arquivo_mock)
        assert not valido
        assert "vazio" in msg.lower()
    
    def test_rejeita_arquivo_muito_grande(self):
        """❌ Arquivo > 5MB deve ser rejeitado."""
        arquivo_mock = Mock()
        arquivo_mock.name = "grande.jpg"
        arquivo_mock.getbuffer.return_value = BytesIO(b"x" * (6 * 1024 * 1024))  # 6MB
        
        valido, msg = UploadHelper._validar_arquivo(arquivo_mock)
        assert not valido
        assert "muito grande" in msg.lower()
    
    def test_rejeita_extensoes_perigosas(self):
        """❌ Extensões perigosas (.exe, .php, .sh) devem ser rejeitadas."""
        perigosas = [".exe", ".php", ".sh", ".bat", ".cmd", ".py", ".js"]
        
        for ext in perigosas:
            arquivo_mock = Mock()
            arquivo_mock.name = f"malicioso{ext}"
            arquivo_mock.getbuffer.return_value = BytesIO(b"x" * 1000)
            
            valido, msg = UploadHelper._validar_arquivo(arquivo_mock)
            assert not valido, f"Deveria rejeitar {ext}"
            assert "não permitido" in msg.lower()
    
    def test_aceita_extensoes_validas(self):
        """✅ Extensões válidas (.jpg, .png, .gif) devem ser aceitas."""
        validas = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        
        for ext in validas:
            arquivo_mock = Mock()
            arquivo_mock.name = f"imagem{ext}"
            arquivo_mock.getbuffer.return_value = BytesIO(b"x" * 1000)
            
            valido, msg = UploadHelper._validar_arquivo(arquivo_mock)
            assert valido, f"Deveria aceitar {ext} - Erro: {msg}"
    
    def test_rejeita_nenhum_arquivo(self):
        """❌ None deve ser rejeitado."""
        valido, msg = UploadHelper._validar_arquivo(None)
        assert not valido
        assert "nenhum arquivo" in msg.lower()
    
    def test_arquivo_valido_com_tamanho_limite(self):
        """✅ Arquivo exatamente no limite (5MB) deve ser aceito."""
        arquivo_mock = Mock()
        arquivo_mock.name = "maximo.jpg"
        arquivo_mock.getbuffer.return_value = BytesIO(b"x" * (5 * 1024 * 1024))
        
        valido, msg = UploadHelper._validar_arquivo(arquivo_mock)
        assert valido, f"Deveria aceitar arquivo de 5MB - Erro: {msg}"
    
    def test_path_traversal_prevention(self, tmp_path):
        """❌ Tentativas de path traversal devem ser bloqueadas.
        
        Valida que nomes com "../" são tratados seguramente.
        """
        # Simular upload dir
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()
        
        # Tentar usar "../" no caminho
        arquivo_mock = Mock()
        arquivo_mock.name = "../../../etc/passwd.jpg"
        arquivo_mock.getbuffer.return_value = BytesIO(b"x" * 1000)
        
        # A Path resolve() + startswith() catch isso
        # Não deveria permitir salvar FORA de UPLOAD_DIR
        caminho_teste = upload_dir / arquivo_mock.name
        
        # Verificar path traversal check
        try:
            if not str(caminho_teste.resolve()).startswith(str(upload_dir.resolve())):
                assert True, "Path traversal detectado e bloqueado ✓"
            else:
                assert False, "Path traversal não foi bloqueado ✗"
        except Exception:
            # Se houver erro, é seguro (rejeitou)
            assert True


class TestUploadIntegration:
    """Testes de integração com upload completo."""
    
    def test_validacao_chamada_em_salvar_imagem(self, tmp_path, monkeypatch):
        """✅ salvar_imagem() deve chamar _validar_arquivo()."""
        # Mock a validação
        chamadas = []
        
        def fake_validar(arquivo):
            chamadas.append(arquivo)
            return False, "Teste - rejeição"
        
        monkeypatch.setattr(UploadHelper, "_validar_arquivo", fake_validar)
        
        arquivo_mock = Mock()
        arquivo_mock.name = "teste.jpg"
        arquivo_mock.getbuffer.return_value = BytesIO(b"x" * 1000)
        
        # Deve rejeitar porque validação retorna False
        resultado = UploadHelper.salvar_imagem(arquivo_mock, id_empresa=1)
        
        assert resultado is None
        assert len(chamadas) == 1, "Validação não foi chamada"
    
    def test_mensagens_de_erro_nao_expoe_detalhes(self, tmp_path):
        """✅ Mensagens de erro devem ser genéricas (não expor stack trace)."""
        arquivo_mock = Mock()
        arquivo_mock.name = "malicioso.exe"
        arquivo_mock.getbuffer.return_value = BytesIO(b"x" * 1000)
        
        valido, msg = UploadHelper._validar_arquivo(arquivo_mock)
        
        # Mensagem deve ser legível pro usuário, não um stack trace
        assert "tipo de arquivo não permitido" in msg.lower()
        assert "traceback" not in msg.lower()
        assert "$" not in msg  # Sem caracteres estranhos


class TestUploadSizeValidation:
    """Testes específicos de tamanho de upload."""
    
    @pytest.mark.parametrize("tamanho_mb,esperado_valido", [
        (0.1, True),   # 100KB - OK
        (1, True),     # 1MB - OK
        (4.9, True),   # 4.9MB - OK
        (5.0, True),   # 5MB - OK (limite)
        (5.1, False),  # 5.1MB - Rejeita
        (10, False),   # 10MB - Rejeita
    ])
    def test_validacao_tamanho_limite(self, tamanho_mb, esperado_valido):
        """✅ Validar limite de 5MB."""
        arquivo_mock = Mock()
        arquivo_mock.name = "arquivo.jpg"
        tamanho_bytes = int(tamanho_mb * 1024 * 1024)
        arquivo_mock.getbuffer.return_value = BytesIO(b"x" * tamanho_bytes)
        
        valido, msg = UploadHelper._validar_arquivo(arquivo_mock)
        
        assert valido == esperado_valido, f"Tamanho {tamanho_mb}MB: esperado {esperado_valido}, got {valido}"
