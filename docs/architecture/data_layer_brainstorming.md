# Data Storage Layer - Brainstorming & Ideas

This document captures informal ideas, considerations, and discussions around the Data Storage and Repository Layer implementation for Issue #108.

## Quick Ideas Dump

### Database Choice
- **SQLite for Day One**: Start simple, proven in production, file-based, no extra services
- **PostgreSQL for Scale**: Consider when we hit 10k+ media items or need advanced querying
- **Hybrid approach**: SQLite default, PostgreSQL optional via config

### Repository Pattern Implementation
- Start with synchronous repositories (simpler, matches current codebase)
- Add async variants later if needed (FastAPI migration, high concurrency needs)
- Keep interfaces abstract enough to swap implementations

### Schema Evolution
- Use Alembic from day one - even small changes benefit from migrations
- Version the schema in code comments
- Keep migration scripts small and focused
- Test migrations both up and down

### Caching Thoughts
- **Phase 1**: In-memory cache (Python dict with TTL) - zero dependencies
- **Phase 2**: Redis optional for multi-instance deployments
- Cache invalidation strategy: explicit invalidation on writes
- Cache keys: structured like `{entity}:{id}:{version}`

### Data Modeling Decisions

#### Media Hierarchy
Option A: Single table inheritance (one `media` table with `type` discriminator)
- Pros: Simple queries, easy to add new types
- Cons: Sparse columns, less type safety

Option B: Table per type (separate `movies`, `series`, `episodes` tables)
- Pros: Clean schema, type-specific columns
- Cons: Complex queries across types, more tables

**Decision**: Start with Option A, can refactor to B if needed

#### Job Status Tracking
Should we use state machine pattern?
- Define valid state transitions
- Prevent invalid state changes
- Log all state changes for debugging

```python
# Valid transitions
VALID_TRANSITIONS = {
    'queued': ['running', 'cancelled'],
    'running': ['completed', 'failed', 'paused'],
    'failed': ['queued', 'cancelled'],  # Allow retry
    'paused': ['running', 'cancelled'],
    'completed': [],  # Terminal state
    'cancelled': []   # Terminal state
}
```

### Testing Strategy Ideas

#### Repository Tests
- Unit tests with in-memory SQLite
- Mock external dependencies
- Test edge cases: null values, max lengths, concurrent access

#### Integration Tests
- Use pytest fixtures for database setup/teardown
- Test migrations forward and backward
- Test transaction rollback scenarios

#### Performance Tests
- Benchmark common queries (get by ID, list with filters)
- Test with realistic data volumes (1k, 10k, 100k records)
- Measure cache effectiveness

### API Design Considerations

#### Repository Methods Naming
Standard CRUD:
- `get_by_id(id)` - single item
- `get_all(filters, limit, offset)` - list with pagination
- `create(entity)` - returns created entity with ID
- `update(entity)` - returns updated entity
- `delete(id)` - returns boolean

Custom queries:
- Use descriptive names: `get_pending_jobs()`, `get_by_external_id()`
- Return types match expectations: single item vs list
- Use Optional[] for nullable returns

#### Error Handling
```python
class RepositoryException(Exception):
    """Base exception for repository errors"""
    pass

class EntityNotFoundException(RepositoryException):
    """Entity not found by ID"""
    pass

class DuplicateEntityException(RepositoryException):
    """Unique constraint violation"""
    pass

class ValidationException(RepositoryException):
    """Data validation failed"""
    pass
```

### Configuration Options

```python
# Simple config approach
DATABASE_CONFIG = {
    'url': os.getenv('DATABASE_URL', 'sqlite:///researcharr.db'),
    'echo': os.getenv('DATABASE_ECHO', 'false').lower() == 'true',
    'pool_size': int(os.getenv('DATABASE_POOL_SIZE', '5')),
}

CACHE_CONFIG = {
    'enabled': os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
    'provider': os.getenv('CACHE_PROVIDER', 'memory'),  # memory or redis
    'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'default_ttl': int(os.getenv('CACHE_TTL', '300')),
}
```

### Migration Strategy

#### Approach 1: Big Bang (Not Recommended)
- Implement everything
- Switch all at once
- High risk, but faster

#### Approach 2: Gradual (Recommended)
1. Implement new layer alongside old
2. Add feature flag: `USE_NEW_DATA_LAYER=false`
3. Migrate one entity at a time:
   - Week 1: Media entities
   - Week 2: Processing jobs
   - Week 3: Queue items
4. Run in parallel with validation
5. Switch over when confidence is high
6. Remove old implementation

#### Approach 3: Strangler Fig Pattern
- New features use new layer
- Gradually migrate old code
- Eventually old layer has no callers
- Remove old code

**Decision**: Approach 2 - Gradual with feature flags

### Backup Strategy Ideas

#### What to Backup
- Full database (all tables)
- Schema version (for restore compatibility)
- Timestamp in filename
- Compression for large databases

#### When to Backup
- Before migrations (automatic)
- Daily at 2 AM (scheduled)
- On-demand via API/CLI
- Before major version upgrades

#### Backup Retention
- Keep last 30 days of daily backups
- Keep last 12 months of monthly backups
- Archive older backups to cold storage

#### Testing Backups
- Automated restore test weekly
- Verify data integrity after restore
- Measure backup/restore time

### Monitoring & Observability

#### Metrics to Track
- Query latency (p50, p95, p99)
- Cache hit/miss ratio
- Connection pool usage
- Transaction duration
- Failed queries count
- Slow queries (> 1s)
- Database size growth
- Table row counts

#### Health Checks
- Database connection alive
- Disk space available (SQLite)
- Connection pool not exhausted
- No long-running transactions
- Migration version current

#### Alerting
- Database unreachable
- Disk space < 10%
- Slow query rate increasing
- Connection pool exhausted
- Failed transaction rate high

### Advanced Features (Future)

#### Read Replicas
- Use read replicas for queries
- Write to primary only
- Handle replication lag

#### Sharding
- Shard by service (Radarr vs Sonarr)
- Shard by date range (time-series data)
- Cross-shard queries are complex

#### Full-Text Search
- Add full-text search on media titles
- Use SQLite FTS5 or PostgreSQL full-text
- Consider Elasticsearch for advanced search

#### Soft Deletes
- Add `deleted_at` column
- Filter out deleted items by default
- Purge old deleted items periodically

#### Audit Trail
- Track who/when/what for all changes
- Store old values for rollback
- Queryable audit log

### Performance Optimization Ideas

#### Indexing Strategy
- Index foreign keys
- Index commonly filtered columns
- Composite indexes for multi-column filters
- Monitor index usage, remove unused

#### Query Optimization
- Use EXPLAIN to analyze queries
- Batch queries instead of N+1
- Use joins instead of multiple queries
- Pagination for large result sets

#### Connection Pooling
- Reuse database connections
- Set appropriate pool size (5-10 for SQLite)
- Monitor connection usage

#### Caching Strategy
- Cache frequently accessed data
- Short TTL for volatile data
- Longer TTL for stable data
- Invalidate on writes

### Edge Cases to Consider

#### Concurrent Access
- Two processes updating same entity
- Use optimistic locking (version field)
- Handle constraint violations gracefully

#### Large Data Sets
- Pagination is mandatory for lists
- Use cursors for stable pagination
- Stream large results instead of loading all

#### Database Corruption
- Regular integrity checks
- Backup before migrations
- Recovery procedures documented

#### Schema Changes
- Backward compatible changes when possible
- Multi-step migrations for breaking changes
- Test migrations on production copy

### Code Organization

```
researcharr/
  core/
    data/
      __init__.py
      models.py           # SQLAlchemy models
      schemas.py          # Pydantic validation schemas
      repositories/
        __init__.py
        base.py          # Base repository interface
        media.py         # Media repository
        jobs.py          # Processing job repository
        queue.py         # Queue repository
      cache/
        __init__.py
        base.py          # Cache provider interface
        memory.py        # In-memory cache
        redis.py         # Redis cache
      migrations/
        env.py
        script.py.mako
        versions/        # Migration scripts
      uow.py            # Unit of Work implementation
      session.py        # Session factory
      backup.py         # Backup manager
      health.py         # Health monitoring
```

### Dependencies to Add

```python
# requirements.txt additions
sqlalchemy>=2.0.0        # ORM
alembic>=1.13.0          # Migrations
pydantic>=2.0.0          # Validation
redis>=5.0.0             # Optional: Redis cache
```

### Documentation Needs

1. **Developer Guide**: How to add new entities
2. **Migration Guide**: How to create and run migrations
3. **Testing Guide**: How to test repositories
4. **Operations Guide**: Backup/restore procedures
5. **Troubleshooting**: Common issues and solutions

### Open Questions & Decisions Needed

1. **Async vs Sync?**
   - Current app is sync (Flask)
   - SQLAlchemy 2.0 supports async
   - Decision: Start sync, add async later if needed

2. **Repository per entity or generic?**
   - Specific: More methods, clearer intent
   - Generic: Less code, more flexible
   - Decision: Specific repositories with shared base

3. **Unit of Work required?**
   - Pros: Transaction management, consistency
   - Cons: Added complexity
   - Decision: Yes, but keep it simple

4. **Pydantic for validation?**
   - Already used elsewhere in app?
   - Alternative: marshmallow, attrs
   - Decision: Pydantic (modern, fast, good DX)

5. **Migration versioning scheme?**
   - Sequential numbers: 001, 002, 003
   - Timestamps: 20231108_120000
   - Alembic default: revision hashes
   - Decision: Alembic default (handles branches)

### Risk Assessment

#### High Risk
- **Data loss during migration**: Mitigate with backups
- **Performance regression**: Mitigate with benchmarks
- **Breaking existing features**: Mitigate with tests

#### Medium Risk
- **Schema changes after launch**: Mitigate with migrations
- **Cache consistency issues**: Mitigate with invalidation
- **Query complexity**: Mitigate with indexes

#### Low Risk
- **Learning curve for team**: Good documentation
- **Tool compatibility**: Use mature tools
- **Vendor lock-in**: Abstract with interfaces

### Success Criteria

**Must Have**
- All existing tests pass
- New data layer tests have >90% coverage
- No performance regression
- Zero data loss in migration
- Documentation complete

**Should Have**
- Migration path documented
- Rollback procedures tested
- Performance improvement vs current
- Monitoring dashboards ready

**Nice to Have**
- Async support for future scaling
- Advanced caching strategies
- Full-text search capability
- Read replica support

### Timeline Estimate

- **Week 1-2**: Core implementation (models, repositories, basic tests)
- **Week 3-4**: Advanced features (caching, validation, migrations)
- **Week 5-6**: Operations (backup, monitoring, documentation)
- **Week 7-8**: Integration & testing (migration, validation, rollout)

**Total**: ~8 weeks for full implementation

### Next Steps

1. ✅ Create architecture document
2. ✅ Brainstorm ideas and considerations
3. [ ] Get feedback from stakeholders
4. [ ] Prioritize features for MVP
5. [ ] Create detailed implementation plan
6. [ ] Set up development environment
7. [ ] Start Phase 1 implementation

## Notes for Implementation

- Keep existing code working while building new layer
- Write tests first (TDD approach)
- Document as we go, not at the end
- Regular check-ins to validate direction
- Be ready to pivot based on feedback
