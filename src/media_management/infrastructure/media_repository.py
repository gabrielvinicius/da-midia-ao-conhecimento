# src/media_management/infrastructure/media_repository.py
from typing import Optional, List, Tuple
from uuid import UUID
import asyncio
from sqlalchemy import select, func, and_, or_, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.media_management.domain.media import Media, MediaStatus
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("media_repository")


class MediaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, media: Media) -> Media:
        """Saves a media entity to the database."""
        self.db.add(media)
        await self.db.commit()
        await self.db.refresh(media)
        return media

    async def find_by_id(self, media_id: str, include_relations: bool = False) -> Optional[Media]:
        """Finds a media entity by its ID with optional eager loading."""
        query = select(Media).where(Media.id == UUID(media_id))
        
        # Eager loading para evitar N+1 queries
        if include_relations:
            query = query.options(
                selectinload(Media.transcriptions),
                selectinload(Media.summaries),
                selectinload(Media.sentiment_analyses),
                selectinload(Media.topic_modelings)
            )
        
        result = await self.db.execute(query)
        media = result.scalar_one_or_none()
        
        if media:
            logger.debug("Media found", media_id=media_id, include_relations=include_relations)
        else:
            logger.warning("Media not found", media_id=media_id)
            
        return media

    async def list_by_user(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 10,
        status_filter: Optional[MediaStatus] = None,
        media_type_filter: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> Tuple[List[Media], int]:
        """Lists media for a user with advanced filtering and pagination."""
        
        # Query base com índice otimizado
        base_query = select(Media).where(Media.user_id == UUID(user_id))
        count_query = select(func.count(Media.id)).where(Media.user_id == UUID(user_id))
        
        # Aplicar filtros usando índices
        filters = []
        if status_filter:
            filters.append(Media.status == status_filter)
        if media_type_filter:
            filters.append(Media.media_type == media_type_filter)
        
        if filters:
            filter_condition = and_(*filters)
            base_query = base_query.where(filter_condition)
            count_query = count_query.where(filter_condition)
        
        # Ordenação
        order_column = getattr(Media, order_by, Media.created_at)
        if order_desc:
            base_query = base_query.order_by(order_column.desc())
        else:
            base_query = base_query.order_by(order_column.asc())
        
        # Paginação
        offset = (page - 1) * limit
        paginated_query = base_query.offset(offset).limit(limit)
        
        # Executar queries em paralelo
        result, count_result = await asyncio.gather(
            self.db.execute(paginated_query),
            self.db.execute(count_query)
        )
        
        media_list = result.scalars().all()
        total_count = count_result.scalar()
        
        logger.debug("Media list retrieved", 
                    user_id=user_id, 
                    page=page, 
                    limit=limit, 
                    total=total_count,
                    returned=len(media_list),
                    filters={"status": status_filter, "type": media_type_filter})
        
        return media_list, total_count

    async def list_all(
        self, 
        page: int = 1, 
        limit: int = 10, 
        search: Optional[str] = None,
        status_filter: Optional[MediaStatus] = None,
        media_type_filter: Optional[str] = None
    ) -> Tuple[List[Media], int]:
        """Lists all media with advanced search and filtering."""
        
        base_query = select(Media)
        count_query = select(func.count(Media.id))
        
        # Aplicar filtros
        filters = []
        
        # Busca textual otimizada com índice GIN
        if search:
            search_condition = or_(
                Media.original_file_path.ilike(f"%{search}%"),
                Media.id.cast(String).ilike(f"%{search}%")
            )
            filters.append(search_condition)
        
        if status_filter:
            filters.append(Media.status == status_filter)
            
        if media_type_filter:
            filters.append(Media.media_type == media_type_filter)
        
        if filters:
            filter_condition = and_(*filters)
            base_query = base_query.where(filter_condition)
            count_query = count_query.where(filter_condition)
        
        # Ordenação por data de criação (usa índice)
        base_query = base_query.order_by(Media.created_at.desc())
        
        # Paginação
        offset = (page - 1) * limit
        paginated_query = base_query.offset(offset).limit(limit)
        
        # Executar queries
        result, count_result = await asyncio.gather(
            self.db.execute(paginated_query),
            self.db.execute(count_query)
        )
        
        media_list = result.scalars().all()
        total_count = count_result.scalar()
        
        logger.debug("All media list retrieved", 
                    page=page, 
                    limit=limit, 
                    search=search,
                    total=total_count,
                    returned=len(media_list))
        
        return media_list, total_count

    async def get_media_statistics(self, user_id: Optional[str] = None) -> dict:
        """Obtém estatísticas de mídia usando consultas otimizadas."""
        
        base_condition = True
        if user_id:
            base_condition = Media.user_id == UUID(user_id)
        
        # Query otimizada para estatísticas usando índices
        stats_query = select(
            Media.status,
            Media.media_type,
            func.count(Media.id).label('count')
        ).where(base_condition).group_by(Media.status, Media.media_type)
        
        result = await self.db.execute(stats_query)
        raw_stats = result.all()
        
        # Processar resultados
        stats = {
            'by_status': {},
            'by_type': {},
            'total': 0
        }
        
        for status, media_type, count in raw_stats:
            stats['by_status'][status] = stats['by_status'].get(status, 0) + count
            stats['by_type'][media_type] = stats['by_type'].get(media_type, 0) + count
            stats['total'] += count
        
        logger.debug("Media statistics calculated", 
                    user_id=user_id, 
                    total=stats['total'])
        
        return stats

    async def delete(self, media_id: UUID) -> bool:
        media = await self.find_by_id(str(media_id))
        if media:
            await self.db.delete(media)
            await self.db.commit()
            return True
        return False
