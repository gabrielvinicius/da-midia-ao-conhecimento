# src/media_management/api/routers.py
import os
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, UploadFile, Depends, HTTPException, status, File, Query
from fastapi.encoders import jsonable_encoder

from src.auth.api.dependencies import get_current_user
from src.auth.domain.user import User
from .dependencies import get_media_service, get_media_queries
from ..application.commands.create_media_command import CreateMediaCommand
from ..application.media_service import MediaService
from ..application.queries.media_queries import MediaQueries
from .schemas import MediaResponse
from ..config.settings import MediaSettings
from .dependencies import get_media_settings

# Import provider validation functions
from src.storage.infrastructure.dependencies import get_available_storage_providers
from src.transcription.infrastructure.dependencies import get_available_speech_recognition_providers
from src.summarization.infrastructure.dependencies import get_available_summarizer_providers

router = APIRouter(
    prefix="/media",
    tags=["Media"],
)

def _get_media_type_from_extension(filename: str) -> str:
    """Determina o tipo de mídia baseado na extensão do arquivo."""
    _, ext = os.path.splitext(filename.lower())
    
    if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        return "VIDEO"
    elif ext in [".mp3", ".wav", ".m4a", ".flac"]:
        return "AUDIO"
    elif ext in [".pdf", ".txt", ".md"]:
        return "TEXT"
    else:
        return "UNKNOWN"

def _validate_providers(
    media_type: str, 
    storage_provider: str, 
    transcription_provider: Optional[str], 
    summarization_provider: Optional[str]
) -> dict:
    """Valida e ajusta os providers baseado no tipo de mídia."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validar storage provider
    available_storage = get_available_storage_providers()
    if storage_provider not in available_storage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Storage provider '{storage_provider}' não disponível. Opções: {available_storage}"
        )
    
    # Validar transcription provider
    validated_transcription = None
    if media_type in ["VIDEO", "AUDIO"]:
        available_transcription = get_available_speech_recognition_providers()
        
        if transcription_provider:
            if transcription_provider not in available_transcription:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Transcription provider '{transcription_provider}' não disponível. Opções: {available_transcription}"
                )
            validated_transcription = transcription_provider
        else:
            # Usar provider padrão para vídeo/áudio
            validated_transcription = "whisper" if "whisper" in available_transcription else available_transcription[0]
            logger.info(f"Using default transcription provider: {validated_transcription}")
    
    elif transcription_provider:
        # Se provider foi especificado para arquivo de texto, ignorar com warning
        logger.warning(f"Transcription provider '{transcription_provider}' ignorado para arquivo de texto")
    
    # Validar summarization provider
    validated_summarization = None
    available_summarization = get_available_summarizer_providers()
    
    if summarization_provider:
        if summarization_provider not in available_summarization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Summarization provider '{summarization_provider}' não disponível. Opções: {available_summarization}"
            )
        validated_summarization = summarization_provider
    else:
        # Usar provider padrão para todos os tipos
        validated_summarization = "huggingface" if "huggingface" in available_summarization else available_summarization[0]
        logger.info(f"Using default summarization provider: {validated_summarization}")
    
    return {
        "storage_provider": storage_provider,
        "transcription_provider": validated_transcription,
        "summarization_provider": validated_summarization,
        "pipeline": _get_processing_pipeline(media_type, validated_transcription, validated_summarization)
    }

def _get_processing_pipeline(media_type: str, transcription_provider: Optional[str], summarization_provider: Optional[str]) -> list:
    """Define o pipeline de processamento baseado no tipo de mídia e providers."""
    pipeline = []
    
    if media_type == "VIDEO":
        pipeline.append("video_processing")  # Extração de áudio
        if transcription_provider:
            pipeline.append(f"transcription_({transcription_provider})")
        if summarization_provider:
            pipeline.append(f"summarization_({summarization_provider})")
        pipeline.append("sentiment_analysis")
        pipeline.append("topic_modeling")
        
    elif media_type == "AUDIO":
        if transcription_provider:
            pipeline.append(f"transcription_({transcription_provider})")
        if summarization_provider:
            pipeline.append(f"summarization_({summarization_provider})")
        pipeline.append("sentiment_analysis")
        pipeline.append("topic_modeling")
        
    elif media_type == "TEXT":
        pipeline.append("text_processing")  # Extração de texto de PDF/TXT
        if summarization_provider:
            pipeline.append(f"summarization_({summarization_provider})")
        pipeline.append("sentiment_analysis")
        pipeline.append("topic_modeling")
    
    return pipeline


@router.post("/", response_model=MediaResponse, status_code=status.HTTP_201_CREATED, summary="Upload a new media file")
async def create_media(
    file: UploadFile = File(..., description="The media file to upload"),
    storage_provider: Optional[str] = Query("local", description="The storage provider to use (e.g., 'local', 's3')."),
    transcription_provider: Optional[str] = Query(None, description="The transcription provider to use for audio/video files."),
    summarization_provider: Optional[str] = Query(None, description="The summarization provider to use."),
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
    settings: MediaSettings = Depends(get_media_settings),
):
    """Uploads a new media file to start a processing pipeline."""
    try:
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"📤 Upload request received:")
        logger.info(f"  - User: {current_user.email}")
        logger.info(f"  - Storage provider: {storage_provider}")
        logger.info(f"  - Transcription provider: {transcription_provider}")
        logger.info(f"  - Summarization provider: {summarization_provider}")
        logger.info(f"  - File object: {file}")
        logger.info(f"  - File type: {type(file)}")
        
        # Validate file exists and has a name
        if not file:
            logger.error("❌ No file received in request")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")
            
        if not file.filename:
            logger.error("❌ File has no filename")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must have a filename")
            
        logger.info(f"  - File name: {file.filename}")
        logger.info(f"  - Content type: {file.content_type}")
        logger.info(f"  - File size: {file.size if hasattr(file, 'size') else 'unknown'}")
        
        # Determinar tipo de mídia e validar providers
        media_type = _get_media_type_from_extension(file.filename)
        logger.info(f"  - Media type detected: {media_type}")
        
        if media_type == "UNKNOWN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de arquivo não suportado. Extensões permitidas: {settings.allowed_extensions}"
            )
        
        # Validar e ajustar providers
        validated_providers = _validate_providers(
            media_type, 
            storage_provider, 
            transcription_provider, 
            summarization_provider
        )
        
        logger.info(f"  - Validated providers: {validated_providers}")
        logger.info(f"  - Processing pipeline: {validated_providers['pipeline']}")
        
        _, file_ext = os.path.splitext(file.filename)
        file_ext_lower = file_ext.lower()
        
        # Validate file extension
        if file_ext_lower not in settings.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Invalid file format '{file_ext}'. Allowed formats: {', '.join(settings.allowed_extensions)}"
            )

        # Read file content to check actual size
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
                detail=f"File too large ({file_size / (1024*1024):.2f}MB). Max size is {settings.max_file_size_mb}MB"
            )
        
        # Validate file is not empty
        if file_size == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File cannot be empty")

        command = CreateMediaCommand(
            user_id=str(current_user.id),
            file=file_content,
            filename=file.filename,
            storage_provider=validated_providers["storage_provider"],
            transcription_provider=validated_providers["transcription_provider"],
            summarization_provider=validated_providers["summarization_provider"]
        )
        media = await media_service.create_media(command)
        
        # Return a safe dictionary with pipeline information
        response_data = {
            "id": str(media.id),
            "original_file_path": media.original_file_path,
            "media_type": media.media_type.value if hasattr(media.media_type, 'value') else str(media.media_type),
            "status": media.status.value if hasattr(media.status, 'value') else str(media.status),
            "storage_provider": media.storage_provider,
            "transcription_provider": media.transcription_provider,
            "summarization_provider": media.summarization_provider,
            "created_at": media.created_at.isoformat() if hasattr(media.created_at, 'isoformat') else str(media.created_at),
            "user_id": str(media.user_id),
            "processing_pipeline": validated_providers["pipeline"],
            "file_size_mb": round(file_size / (1024 * 1024), 2)
        }
        
        logger.info(f"✅ Upload successful - Media {media.id} created with pipeline: {validated_providers['pipeline']}")
        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Upload error for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Upload failed: {type(e).__name__}: {str(e)}"
        ) from e


@router.get("/", response_model=List[MediaResponse], summary="List all media for the current user")
async def get_all_media(
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media_list = await media_queries.list_by_user(user_id=str(current_user.id))
    
    # Convert to safe dictionary format to avoid recursion
    return [
        {
            "id": str(media.id),
            "original_file_path": media.original_file_path,
            "media_type": media.media_type.value if hasattr(media.media_type, 'value') else str(media.media_type),
            "status": media.status.value if hasattr(media.status, 'value') else str(media.status),
            "storage_provider": media.storage_provider,
            "transcription_provider": media.transcription_provider,
            "summarization_provider": media.summarization_provider,
            "created_at": media.created_at.isoformat() if hasattr(media.created_at, 'isoformat') else str(media.created_at),
            "user_id": str(media.user_id)
        }
        for media in media_list
    ]


@router.get("/{media_id}", response_model=MediaResponse, summary="Get a media item by its ID")
async def get_media_by_id(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    media = await media_queries.get_by_id(str(media_id))
    if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
        raise HTTPException(status_code=404, detail="Media not found or not authorized")
    
    # Return safe dictionary format to avoid recursion
    return {
        "id": str(media.id),
        "original_file_path": media.original_file_path,
        "media_type": media.media_type.value if hasattr(media.media_type, 'value') else str(media.media_type),
        "status": media.status.value if hasattr(media.status, 'value') else str(media.status),
        "storage_provider": media.storage_provider,
        "transcription_provider": media.transcription_provider,
        "summarization_provider": media.summarization_provider,
        "created_at": media.created_at.isoformat() if hasattr(media.created_at, 'isoformat') else str(media.created_at),
        "user_id": str(media.user_id)
    }


@router.post("/{media_id}/reprocess", summary="Reprocess a media item")
async def reprocess_media(
    media_id: UUID,
    current_user: User = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
    media_queries: MediaQueries = Depends(get_media_queries),
):
    """Reprocess a media item to regenerate transcription, summary, etc."""
    try:
        # Verificar se o media existe e pertence ao usuário
        media = await media_queries.get_by_id(str(media_id))
        if not media or (str(media.user_id) != str(current_user.id) and current_user.role.value != "admin"):
            raise HTTPException(status_code=404, detail="Media not found or not authorized")
        
        # Chamar o serviço de reprocessamento
        await media_service.reprocess_media(media_id)
        
        return {"message": f"Media {media_id} has been queued for reprocessing"}
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Reprocess error for media {media_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Reprocessing failed: {type(e).__name__}: {str(e)}"
        ) from e
