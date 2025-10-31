# src/shared/infrastructure/async_file_handler.py
"""
Sistema de manipulação de arquivos assíncrono otimizado.
Usa aiofiles para I/O não-bloqueante e buffering inteligente.
"""

import aiofiles
import aiofiles.os
import asyncio
from typing import Optional, BinaryIO, AsyncGenerator, Dict, Any
from pathlib import Path
import hashlib
import mimetypes
from datetime import datetime

from src.shared.infrastructure.logging_config import get_logger
from src.shared.infrastructure.cache import cache_manager, CacheConfig

logger = get_logger("async_file_handler")


class AsyncFileHandler:
    """Handler assíncrono otimizado para operações de arquivo."""
    
    CHUNK_SIZE = 64 * 1024  # 64KB chunks para streaming
    BUFFER_SIZE = 8 * 1024 * 1024  # 8MB buffer para operações grandes
    
    def __init__(self):
        self.temp_dir = Path("/tmp/media_processing")
        self.temp_dir.mkdir(exist_ok=True)
    
    async def read_file_chunks(
        self, 
        file_path: str, 
        chunk_size: int = CHUNK_SIZE
    ) -> AsyncGenerator[bytes, None]:
        """
        Lê arquivo em chunks assíncronos para streaming eficiente.
        
        Args:
            file_path: Caminho do arquivo
            chunk_size: Tamanho do chunk em bytes
            
        Yields:
            Chunks de bytes do arquivo
        """
        try:
            async with aiofiles.open(file_path, 'rb') as file:
                while chunk := await file.read(chunk_size):
                    yield chunk
                    
        except FileNotFoundError:
            logger.error("File not found for streaming", file_path=file_path)
            raise
        except Exception as e:
            logger.error("Error streaming file", file_path=file_path, error=str(e))
            raise
    
    async def write_file_from_stream(
        self, 
        file_path: str, 
        data_stream: AsyncGenerator[bytes, None],
        expected_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Escreve arquivo a partir de stream assíncrono com verificações.
        
        Args:
            file_path: Caminho de destino
            data_stream: Stream de dados
            expected_size: Tamanho esperado para validação
            
        Returns:
            Dict com informações do arquivo salvo
        """
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        written_bytes = 0
        hash_md5 = hashlib.md5()
        
        try:
            async with aiofiles.open(file_path, 'wb') as file:
                async for chunk in data_stream:
                    await file.write(chunk)
                    written_bytes += len(chunk)
                    hash_md5.update(chunk)
                    
                    # Verificar se não excedeu tamanho esperado
                    if expected_size and written_bytes > expected_size:
                        raise ValueError(f"File size exceeded expected {expected_size} bytes")
            
            # Verificar se arquivo foi completamente escrito
            if expected_size and written_bytes != expected_size:
                await aiofiles.os.remove(file_path)
                raise ValueError(f"Incomplete file write: {written_bytes}/{expected_size} bytes")
            
            # Obter informações do arquivo
            file_stats = await aiofiles.os.stat(file_path)
            file_info = {
                "path": file_path,
                "size": file_stats.st_size,
                "md5_hash": hash_md5.hexdigest(),
                "created_at": datetime.fromtimestamp(file_stats.st_ctime),
                "mime_type": mimetypes.guess_type(file_path)[0]
            }
            
            logger.info("File written successfully", 
                       file_path=file_path, 
                       size=file_stats.st_size,
                       md5=file_info["md5_hash"])
            
            return file_info
            
        except Exception as e:
            # Limpar arquivo parcial em caso de erro
            try:
                await aiofiles.os.remove(file_path)
            except:
                pass
            
            logger.error("Error writing file from stream", 
                        file_path=file_path, 
                        written_bytes=written_bytes,
                        error=str(e))
            raise
    
    async def copy_file_async(
        self, 
        source_path: str, 
        dest_path: str, 
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """
        Copia arquivo de forma assíncrona com verificação opcional de checksum.
        
        Args:
            source_path: Arquivo origem
            dest_path: Arquivo destino
            verify_checksum: Se deve verificar integridade
            
        Returns:
            Informações da operação
        """
        source_path_obj = Path(source_path)
        dest_path_obj = Path(dest_path)
        
        if not source_path_obj.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        dest_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Obter hash do arquivo origem se verificação estiver habilitada
        source_hash = None
        if verify_checksum:
            source_hash = await self._calculate_file_hash(source_path)
        
        copied_bytes = 0
        
        try:
            async with aiofiles.open(source_path, 'rb') as src:
                async with aiofiles.open(dest_path, 'wb') as dst:
                    while chunk := await src.read(self.CHUNK_SIZE):
                        await dst.write(chunk)
                        copied_bytes += len(chunk)
            
            # Verificar integridade se solicitado
            if verify_checksum:
                dest_hash = await self._calculate_file_hash(dest_path)
                if source_hash != dest_hash:
                    await aiofiles.os.remove(dest_path)
                    raise ValueError("File integrity check failed: checksum mismatch")
            
            # Obter informações do arquivo copiado
            dest_stats = await aiofiles.os.stat(dest_path)
            
            result = {
                "source_path": source_path,
                "dest_path": dest_path,
                "size": dest_stats.st_size,
                "copied_bytes": copied_bytes,
                "verified": verify_checksum,
                "completed_at": datetime.utcnow()
            }
            
            if verify_checksum:
                result["checksum"] = source_hash
            
            logger.info("File copied successfully", **result)
            return result
            
        except Exception as e:
            # Limpar arquivo parcial
            try:
                await aiofiles.os.remove(dest_path)
            except:
                pass
            
            logger.error("Error copying file", 
                        source_path=source_path,
                        dest_path=dest_path,
                        copied_bytes=copied_bytes,
                        error=str(e))
            raise
    
    async def delete_file_async(self, file_path: str) -> bool:
        """
        Remove arquivo de forma assíncrona.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se removido com sucesso
        """
        try:
            await aiofiles.os.remove(file_path)
            logger.info("File deleted successfully", file_path=file_path)
            return True
            
        except FileNotFoundError:
            logger.warning("File not found for deletion", file_path=file_path)
            return False
            
        except Exception as e:
            logger.error("Error deleting file", file_path=file_path, error=str(e))
            return False
    
    async def get_file_info(self, file_path: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Obtém informações do arquivo com cache opcional.
        
        Args:
            file_path: Caminho do arquivo
            use_cache: Se deve usar cache
            
        Returns:
            Informações do arquivo ou None se não encontrado
        """
        cache_key = f"file_info_{hashlib.md5(file_path.encode()).hexdigest()}"
        
        # Tentar cache primeiro
        if use_cache:
            cached_info = await cache_manager.cache.get(
                CacheConfig.PREFIXES["api_response"], 
                cache_key
            )
            if cached_info:
                logger.debug("File info found in cache", file_path=file_path)
                return cached_info
        
        try:
            file_stats = await aiofiles.os.stat(file_path)
            
            file_info = {
                "path": file_path,
                "size": file_stats.st_size,
                "created_at": datetime.fromtimestamp(file_stats.st_ctime),
                "modified_at": datetime.fromtimestamp(file_stats.st_mtime),
                "mime_type": mimetypes.guess_type(file_path)[0],
                "exists": True
            }
            
            # Cachear informações
            if use_cache:
                await cache_manager.cache.set(
                    CacheConfig.PREFIXES["api_response"],
                    cache_key,
                    file_info,
                    CacheConfig.MEDIUM_TTL
                )
            
            return file_info
            
        except FileNotFoundError:
            return {"path": file_path, "exists": False}
        except Exception as e:
            logger.error("Error getting file info", file_path=file_path, error=str(e))
            return None
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calcula hash MD5 do arquivo de forma assíncrona."""
        hash_md5 = hashlib.md5()
        
        async with aiofiles.open(file_path, 'rb') as file:
            while chunk := await file.read(self.CHUNK_SIZE):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    async def create_temp_file(self, content: bytes, suffix: str = "") -> str:
        """
        Cria arquivo temporário com conteúdo.
        
        Args:
            content: Conteúdo do arquivo
            suffix: Sufixo do arquivo
            
        Returns:
            Caminho do arquivo temporário
        """
        import tempfile
        
        # Gerar nome único
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        hash_part = hashlib.md5(content[:1024]).hexdigest()[:8]
        filename = f"temp_{timestamp}_{hash_part}{suffix}"
        
        temp_path = self.temp_dir / filename
        
        async with aiofiles.open(temp_path, 'wb') as file:
            await file.write(content)
        
        logger.debug("Temporary file created", path=str(temp_path), size=len(content))
        return str(temp_path)
    
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Limpa arquivos temporários antigos.
        
        Args:
            max_age_hours: Idade máxima em horas
            
        Returns:
            Número de arquivos removidos
        """
        removed_count = 0
        max_age_seconds = max_age_hours * 3600
        current_time = datetime.utcnow().timestamp()
        
        try:
            for file_path in self.temp_dir.glob("temp_*"):
                file_stats = await aiofiles.os.stat(file_path)
                file_age = current_time - file_stats.st_ctime
                
                if file_age > max_age_seconds:
                    await aiofiles.os.remove(file_path)
                    removed_count += 1
            
            if removed_count > 0:
                logger.info("Temporary files cleaned up", removed_count=removed_count)
            
        except Exception as e:
            logger.error("Error cleaning up temp files", error=str(e))
        
        return removed_count


# Instância global
async_file_handler = AsyncFileHandler()