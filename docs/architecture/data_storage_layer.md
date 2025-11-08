# Data Storage and Repository Layer Architecture

## Overview

This document outlines the design and implementation strategy for the Data Storage and Repository Layer for researcharr, addressing Issue #108. The goal is to create a flexible, maintainable, and performant data persistence layer that supports the application's media processing needs.

## Current State Analysis

### Existing Database Implementation

Currently, researcharr has two database implementations:

1. **Core Database Service** (`researcharr/core/services.py`):
   - Manages `radarr_queue` and `sonarr_queue` tables
   - Uses raw SQLite connections
   - Basic initialization and health checking

2. **WebUI Database** (`researcharr/db.py`):
   - Manages `webui_users` table
   - Single-user authentication storage
   - Simple CRUD operations

### Limitations of Current Approach

- **No abstraction**: Direct SQL queries throughout the codebase
- **No migrations**: Schema changes require manual SQL
- **Limited data models**: Only queue and user tables
- **No caching**: All queries hit the database
- **No validation**: Data integrity depends on application logic
- **Tight coupling**: Business logic tightly coupled to SQLite

## Proposed Architecture

### 1. Data Models

#### Core Entities

```python
# Media Models
- Media (base class)
  - id: UUID
  - title: str
  - type: enum (movie, series, episode)
  - external_id: str (TMDB, TVDB, etc.)
  - status: enum (pending, processing, completed, failed)
  - metadata: JSON
  - created_at: datetime
  - updated_at: datetime

- Movie(Media)
  - year: int
  - imdb_id: str
  - tmdb_id: int
  - runtime_minutes: int

- Series(Media)
  - tvdb_id: int
  - seasons: int
  - episodes: int

- Episode(Media)
  - series_id: FK(Series)
  - season_number: int
  - episode_number: int
  - air_date: date

# Processing State Models
- ProcessingJob
  - id: UUID
  - media_id: FK(Media)
  - job_type: enum (search, download, verify)
  - status: enum (queued, running, completed, failed)
  - priority: int
  - retry_count: int
  - max_retries: int
  - error_message: str
  - started_at: datetime
  - completed_at: datetime
  - metadata: JSON

- ProcessingHistory
  - id: UUID
  - job_id: FK(ProcessingJob)
  - media_id: FK(Media)
  - action: str
  - status: str
  - details: JSON
  - timestamp: datetime

# Queue Models (Enhanced)
- QueueItem
  - id: UUID
  - media_id: FK(Media)
  - service: enum (radarr, sonarr)
  - priority: int
  - added_at: datetime
  - last_processed: datetime
  - retry_count: int
  - next_retry_at: datetime
```

#### Support Entities

```python
- Configuration
  - id: UUID
  - key: str (unique)
  - value: str
  - value_type: enum (string, int, bool, json)
  - description: str
  - created_at: datetime
  - updated_at: datetime

- AuditLog
  - id: UUID
  - entity_type: str
  - entity_id: UUID
  - action: enum (create, update, delete)
  - user_id: str (nullable)
  - changes: JSON
  - timestamp: datetime

- CacheEntry
  - key: str (primary key)
  - value: bytes
  - expiry: datetime
  - created_at: datetime
```

### 2. Repository Pattern

#### Base Repository Interface

```python
class IRepository[T]:
    """Generic repository interface"""
    
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get entity by ID"""
        pass
    
    async def get_all(self, filters: Dict = None, 
                     limit: int = None, 
                     offset: int = None) -> List[T]:
        """Get all entities matching filters"""
        pass
    
    async def create(self, entity: T) -> T:
        """Create new entity"""
        pass
    
    async def update(self, entity: T) -> T:
        """Update existing entity"""
        pass
    
    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID"""
        pass
    
    async def exists(self, id: UUID) -> bool:
        """Check if entity exists"""
        pass
    
    async def count(self, filters: Dict = None) -> int:
        """Count entities matching filters"""
        pass
```

#### Specialized Repositories

```python
class IMediaRepository(IRepository[Media]):
    """Media-specific repository operations"""
    
    async def get_by_external_id(self, external_id: str, 
                                  type: str) -> Optional[Media]:
        """Get media by external ID (TMDB, TVDB, etc.)"""
        pass
    
    async def get_by_status(self, status: str) -> List[Media]:
        """Get all media with specific status"""
        pass
    
    async def search(self, query: str, 
                     media_type: str = None) -> List[Media]:
        """Search media by title"""
        pass

class IProcessingJobRepository(IRepository[ProcessingJob]):
    """Processing job repository operations"""
    
    async def get_pending_jobs(self, limit: int = None) -> List[ProcessingJob]:
        """Get pending jobs ordered by priority"""
        pass
    
    async def get_jobs_by_media(self, media_id: UUID) -> List[ProcessingJob]:
        """Get all jobs for a media item"""
        pass
    
    async def get_failed_jobs(self) -> List[ProcessingJob]:
        """Get all failed jobs"""
        pass
    
    async def mark_as_completed(self, job_id: UUID) -> bool:
        """Mark job as completed"""
        pass

class IQueueRepository(IRepository[QueueItem]):
    """Queue repository operations"""
    
    async def get_next_items(self, service: str, 
                             limit: int = 10) -> List[QueueItem]:
        """Get next items to process for a service"""
        pass
    
    async def update_last_processed(self, item_id: UUID) -> bool:
        """Update last processed timestamp"""
        pass
    
    async def increment_retry_count(self, item_id: UUID) -> bool:
        """Increment retry count"""
        pass
```

### 3. Database Schema and Migrations

#### Migration Framework

Use **Alembic** for database migrations:

```python
# migrations/env.py
from alembic import context
from researcharr.core.data.models import Base

target_metadata = Base.metadata

def run_migrations_online():
    """Run migrations in 'online' mode"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

#### Initial Schema Structure

```sql
-- Core tables
CREATE TABLE media (
    id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    type VARCHAR(50) NOT NULL,
    external_id VARCHAR(100),
    status VARCHAR(50) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT unique_external_id UNIQUE (external_id, type)
);

CREATE INDEX idx_media_type ON media(type);
CREATE INDEX idx_media_status ON media(status);
CREATE INDEX idx_media_external_id ON media(external_id);

-- Processing jobs
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY,
    media_id UUID REFERENCES media(id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_media_id ON processing_jobs(media_id);
CREATE INDEX idx_jobs_priority ON processing_jobs(priority DESC);

-- Queue items
CREATE TABLE queue_items (
    id UUID PRIMARY KEY,
    media_id UUID REFERENCES media(id) ON DELETE CASCADE,
    service VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 0,
    added_at TIMESTAMP NOT NULL,
    last_processed TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_queue_service ON queue_items(service);
CREATE INDEX idx_queue_priority ON queue_items(priority DESC);
CREATE INDEX idx_queue_next_retry ON queue_items(next_retry_at);
```

### 4. Data Access Layer with SQLAlchemy

#### SQLAlchemy Models

```python
from sqlalchemy import Column, String, Integer, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

Base = declarative_base()

class MediaModel(Base):
    __tablename__ = 'media'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    type = Column(String(50), nullable=False)
    external_id = Column(String(100))
    status = Column(String(50), nullable=False, default='pending')
    metadata = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, 
                       onupdate=datetime.utcnow)
    
    # Relationships
    processing_jobs = relationship("ProcessingJobModel", back_populates="media")
    queue_items = relationship("QueueItemModel", back_populates="media")
```

#### Unit of Work Pattern

```python
class UnitOfWork:
    """Manages database transactions and repository lifecycle"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session = None
    
    async def __aenter__(self):
        self.session = self.session_factory()
        self._media_repo = MediaRepository(self.session)
        self._jobs_repo = ProcessingJobRepository(self.session)
        self._queue_repo = QueueRepository(self.session)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        await self.session.close()
    
    async def commit(self):
        await self.session.commit()
    
    async def rollback(self):
        await self.session.rollback()
    
    @property
    def media(self) -> IMediaRepository:
        return self._media_repo
    
    @property
    def jobs(self) -> IProcessingJobRepository:
        return self._jobs_repo
    
    @property
    def queue(self) -> IQueueRepository:
        return self._queue_repo
```

### 5. Caching Layer

#### Cache Strategy

```python
class CacheStrategy(Enum):
    NONE = "none"           # No caching
    READ_THROUGH = "read_through"  # Cache on read
    WRITE_THROUGH = "write_through"  # Update cache on write
    WRITE_BEHIND = "write_behind"   # Async cache updates

class ICacheProvider:
    """Cache provider interface"""
    
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    async def set(self, key: str, value: Any, ttl: int = None):
        pass
    
    async def delete(self, key: str):
        pass
    
    async def clear(self, pattern: str = None):
        pass
    
    async def exists(self, key: str) -> bool:
        pass

class RedisCacheProvider(ICacheProvider):
    """Redis-based cache implementation"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        if data:
            return pickle.loads(data)
        return None

class InMemoryCacheProvider(ICacheProvider):
    """In-memory cache for development/testing"""
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
```

#### Caching Decorator

```python
def cached(ttl: int = 300, key_prefix: str = None):
    """Decorator for caching repository methods"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            cache = get_cache_provider()
            
            # Generate cache key
            key = f"{key_prefix or func.__name__}:{args}:{kwargs}"
            
            # Try cache first
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Cache result
            await cache.set(key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator

# Usage
class MediaRepository(IMediaRepository):
    @cached(ttl=600, key_prefix="media")
    async def get_by_id(self, id: UUID) -> Optional[Media]:
        # Implementation
        pass
```

### 6. Data Validation and Constraints

#### Pydantic Models for Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class MediaCreate(BaseModel):
    """Validation model for creating media"""
    
    title: str = Field(..., min_length=1, max_length=500)
    type: str = Field(..., pattern="^(movie|series|episode)$")
    external_id: Optional[str] = Field(None, max_length=100)
    metadata: Optional[dict] = None
    
    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @validator('metadata')
    def validate_metadata(cls, v):
        if v and not isinstance(v, dict):
            raise ValueError('Metadata must be a dictionary')
        return v

class MediaUpdate(BaseModel):
    """Validation model for updating media"""
    
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    status: Optional[str] = None
    metadata: Optional[dict] = None

class ProcessingJobCreate(BaseModel):
    """Validation model for creating processing jobs"""
    
    media_id: UUID
    job_type: str = Field(..., pattern="^(search|download|verify)$")
    priority: int = Field(default=0, ge=0, le=100)
    max_retries: int = Field(default=3, ge=0, le=10)
```

#### Database Constraints

```python
# In SQLAlchemy models
class MediaModel(Base):
    # ... existing fields ...
    
    __table_args__ = (
        CheckConstraint('length(title) > 0', name='title_not_empty'),
        CheckConstraint("type IN ('movie', 'series', 'episode')", 
                       name='valid_media_type'),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", 
                       name='valid_status'),
        UniqueConstraint('external_id', 'type', name='unique_external_media'),
    )
```

### 7. Backup and Recovery

#### Backup Strategy

```python
class BackupManager:
    """Manages database backups and recovery"""
    
    def __init__(self, db_url: str, backup_dir: str):
        self.db_url = db_url
        self.backup_dir = backup_dir
    
    async def create_backup(self, backup_name: str = None) -> str:
        """Create a full database backup"""
        if not backup_name:
            backup_name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = os.path.join(self.backup_dir, f"{backup_name}.sql")
        
        # For SQLite
        if self.db_url.startswith('sqlite'):
            import shutil
            db_path = self.db_url.replace('sqlite:///', '')
            shutil.copy2(db_path, backup_path)
        
        # For PostgreSQL
        elif self.db_url.startswith('postgresql'):
            subprocess.run([
                'pg_dump',
                '-f', backup_path,
                self.db_url
            ])
        
        return backup_path
    
    async def restore_backup(self, backup_path: str):
        """Restore database from backup"""
        pass
    
    async def list_backups(self) -> List[dict]:
        """List all available backups"""
        backups = []
        for filename in os.listdir(self.backup_dir):
            if filename.endswith('.sql'):
                filepath = os.path.join(self.backup_dir, filename)
                stat = os.stat(filepath)
                backups.append({
                    'name': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime)
                })
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    async def cleanup_old_backups(self, keep_last: int = 10):
        """Delete old backups, keeping only the most recent"""
        backups = await self.list_backups()
        if len(backups) > keep_last:
            for backup in backups[keep_last:]:
                os.remove(backup['path'])
```

#### Scheduled Backups

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class BackupScheduler:
    """Schedule automatic database backups"""
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        # Daily backup at 2 AM
        self.scheduler.add_job(
            self.backup_manager.create_backup,
            'cron',
            hour=2,
            minute=0
        )
        
        # Weekly cleanup
        self.scheduler.add_job(
            self.backup_manager.cleanup_old_backups,
            'cron',
            day_of_week='sun',
            hour=3,
            minute=0
        )
        
        self.scheduler.start()
```

### 8. Database Health Monitoring

#### Health Check Service

```python
class DatabaseHealthService:
    """Monitor database health and performance"""
    
    def __init__(self, engine):
        self.engine = engine
        self._metrics = {
            'query_count': 0,
            'slow_queries': [],
            'connection_errors': 0,
            'last_check': None
        }
    
    async def check_health(self) -> dict:
        """Comprehensive health check"""
        health = {
            'status': 'healthy',
            'checks': {},
            'timestamp': datetime.utcnow()
        }
        
        # Check connection
        try:
            async with self.engine.connect() as conn:
                await conn.execute("SELECT 1")
            health['checks']['connection'] = 'ok'
        except Exception as e:
            health['checks']['connection'] = f'failed: {e}'
            health['status'] = 'unhealthy'
        
        # Check disk space (for SQLite)
        if self.db_url.startswith('sqlite'):
            db_path = self.db_url.replace('sqlite:///', '')
            stat = os.statvfs(os.path.dirname(db_path))
            free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            health['checks']['disk_space_gb'] = free_space_gb
            if free_space_gb < 1.0:
                health['status'] = 'warning'
        
        # Check table sizes
        table_sizes = await self._get_table_sizes()
        health['checks']['table_sizes'] = table_sizes
        
        # Check slow queries
        if len(self._metrics['slow_queries']) > 0:
            health['checks']['slow_queries'] = len(self._metrics['slow_queries'])
        
        self._metrics['last_check'] = datetime.utcnow()
        return health
    
    async def _get_table_sizes(self) -> dict:
        """Get size of each table"""
        sizes = {}
        async with self.engine.connect() as conn:
            for table in Base.metadata.tables.keys():
                result = await conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                sizes[table] = count
        return sizes
    
    def record_slow_query(self, query: str, duration: float):
        """Record a slow query for monitoring"""
        if duration > 1.0:  # queries taking > 1 second
            self._metrics['slow_queries'].append({
                'query': query,
                'duration': duration,
                'timestamp': datetime.utcnow()
            })
            # Keep only last 100 slow queries
            if len(self._metrics['slow_queries']) > 100:
                self._metrics['slow_queries'] = self._metrics['slow_queries'][-100:]
```

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up SQLAlchemy and Alembic
- [ ] Define base models and repository interfaces
- [ ] Create initial database schema
- [ ] Implement basic CRUD operations
- [ ] Add unit tests for repositories

### Phase 2: Advanced Features (Week 3-4)
- [ ] Implement Unit of Work pattern
- [ ] Add caching layer with Redis support
- [ ] Implement data validation with Pydantic
- [ ] Add database constraints
- [ ] Integration tests

### Phase 3: Operational Features (Week 5-6)
- [ ] Implement backup and recovery
- [ ] Add database health monitoring
- [ ] Create migration scripts
- [ ] Performance optimization
- [ ] Documentation

### Phase 4: Integration (Week 7-8)
- [ ] Integrate with existing services
- [ ] Migrate existing data
- [ ] Update API endpoints
- [ ] End-to-end testing
- [ ] Production readiness review

## Testing Strategy

### Unit Tests
- Repository implementations
- Data validation
- Cache providers
- Backup/restore functionality

### Integration Tests
- Database operations with real SQLite/PostgreSQL
- Cache integration
- Migration testing
- Transaction handling

### Performance Tests
- Query performance benchmarks
- Cache hit rate measurements
- Concurrent access scenarios
- Large dataset handling

## Configuration

```yaml
# config.yml
database:
  url: "sqlite:///researcharr.db"  # or postgresql://...
  pool_size: 5
  max_overflow: 10
  echo: false  # SQLAlchemy query logging
  
migrations:
  directory: "migrations"
  auto_generate: true
  
cache:
  enabled: true
  provider: "redis"  # or "memory"
  redis_url: "redis://localhost:6379/0"
  default_ttl: 300
  
backup:
  enabled: true
  directory: "backups"
  schedule: "0 2 * * *"  # Daily at 2 AM
  keep_last: 30
  
monitoring:
  enabled: true
  slow_query_threshold: 1.0  # seconds
  health_check_interval: 60  # seconds
```

## Migration Path from Current Implementation

### Step 1: Parallel Implementation
- New data layer runs alongside existing db.py
- No breaking changes to existing code
- Feature flag to enable new implementation

### Step 2: Gradual Migration
- Migrate one table at a time
- Keep backward compatibility
- Extensive testing at each step

### Step 3: Final Cutover
- Remove old implementation
- Update all references
- Clean up deprecated code

## Security Considerations

1. **SQL Injection**: SQLAlchemy parameterized queries
2. **Access Control**: Repository-level permissions
3. **Audit Logging**: Track all data modifications
4. **Encryption**: Support for encrypted database connections
5. **Secrets Management**: External secrets for DB credentials

## Performance Targets

- **Query Response Time**: < 100ms for 95th percentile
- **Cache Hit Rate**: > 80% for frequently accessed data
- **Transaction Throughput**: > 1000 operations/second
- **Concurrent Connections**: Support 50+ simultaneous connections
- **Database Size**: Efficient operation up to 10GB

## Open Questions

1. Should we support PostgreSQL from day one or start with SQLite only?
2. What's the priority for async vs sync implementation?
3. Should we use SQLAlchemy async or stick with sync for simplicity?
4. Redis requirement: required or optional?
5. Migration strategy: Big bang or gradual?

## Success Metrics

- [ ] All tests passing with >90% coverage
- [ ] Zero breaking changes to existing API
- [ ] Performance meets or exceeds targets
- [ ] Documentation complete and accurate
- [ ] Successfully deployed to production
- [ ] Zero critical issues in first week

## References

- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Alembic Documentation: https://alembic.sqlalchemy.org/
- Repository Pattern: https://martinfowler.com/eaaCatalog/repository.html
- Unit of Work Pattern: https://martinfowler.com/eaaCatalog/unitOfWork.html
