---
name: backend-development-principles
description: Guiding principles for AI-assisted Python backend development. Use when building APIs with FastAPI, designing distributed systems, implementing microservices, or working on any Python backend code. Provides architectural patterns, code standards, testing strategies, and AI workflow integration. Apply when (1) creating new backend services or APIs, (2) refactoring existing Python backend code, (3) designing system architecture, (4) implementing database patterns, (5) writing tests for backend code, or (6) reviewing AI-generated backend code.
---

# Backend Development Principles

Principles for production-quality Python backend development with AI assistance.

## Core Philosophy

**Willison's Golden Rule**: Never commit AI-generated code you cannot fully explain. If you can't articulate what every line does and why, don't ship it.

**Spec-Driven Development**: Before writing code, generate a `spec.md` with requirements, architecture decisions, and constraints. The spec guides implementation; implementation validates the spec.

**Architecture First, Code Second**: AI generates code for patterns you specify—it cannot reason about production trade-offs. You provide the architectural judgment; AI provides velocity.

## System Design Principles

### Distributed Systems
- Specify consistency requirements (strong, eventual, causal) before implementing data flows
- Design for failure: circuit breakers, retries with exponential backoff and jitter, graceful degradation
- Prefer idempotent operations—repeated calls produce the same result
- Document CAP theorem trade-offs explicitly

### Service Architecture
- Start monolith, extract services only when team/scaling boundaries demand it
- Service boundaries follow domain boundaries, not technical layers
- Each service owns its data—no shared databases between services
- Design APIs for backward compatibility from day one

### Data Patterns
- Separate read and write models when query patterns diverge (CQRS)
- Event sourcing for audit requirements or complex state reconstruction
- Define cache invalidation strategy before implementing caching
- Database choice follows access patterns, not familiarity

## Python/FastAPI Standards

### Project Structure
```
src/
├── api/v1/           # Thin route handlers
├── core/             # Config, security, dependencies
├── domain/           # Business logic, domain models
├── infrastructure/   # Database, external services
├── schemas/          # Pydantic API contracts
└── tests/
```

### Code Patterns
- Route handlers are thin: validate → call domain → return response
- Dependency injection for sessions, auth, shared resources
- Pydantic models for ALL API boundaries
- Async for I/O-bound, sync for CPU-bound
- Background tasks for non-immediate operations

### Type Safety
- Enable `strict` mode in pyproject.toml
- Type hints on ALL function signatures
- `TypedDict` for complex dictionary structures
- Prefer dataclasses/Pydantic over raw dicts

### Error Handling
- Custom exceptions mapping to HTTP status codes
- Centralized exception handler middleware
- Never expose internal errors to consumers
- Structured responses: `{"error": {"code": "...", "message": "...", "details": {...}}}`

## Testing Strategy

Target: 80%+ coverage on domain logic, 60%+ overall.

```bash
# Single file (fast iteration)
pytest tests/unit/test_user_service.py -v

# With coverage
pytest tests/unit/test_user_service.py --cov=src/domain/user -v
```

For detailed testing patterns, see [references/testing.md](references/testing.md).

## API Design

For comprehensive REST conventions, response standards, and versioning, see [references/api-design.md](references/api-design.md).

## Security Principles

**Secure by Design**: Security is integrated from the start, not bolted on. Document threat models during planning. Every design decision considers attack surface.

**Least Privilege**: Users and workflows get exactly the minimum permissions required—nothing more. Privilege escalation requires explicit auditing.

**Defense in Depth**: Multiple layers of security controls. No single point of failure in security architecture.

For detailed security patterns, input validation, file handling, and error handling, see [references/security.md](references/security.md).

## Do NOT

- Do NOT use `*` imports
- Do NOT put business logic in route handlers
- Do NOT use `Any` type without justification
- Do NOT commit commented-out code
- Do NOT use raw SQL strings
- Do NOT hardcode configuration
- Do NOT skip migrations
- Do NOT catch generic `Exception` without re-raising or logging

## AI Workflow Integration

### Before Prompting
1. Write spec.md with requirements and constraints
2. Define data model and API contract
3. Identify applicable architectural patterns
4. List explicit constraints (versions, existing patterns)

### Prompt Structure
```
Context: [system purpose, tech stack, constraints]
Task: [specific deliverable]
Patterns: [reference existing code or patterns]
Constraints: [what NOT to do, versions]
Output: [expected format]
```

### After Generation
- Verify against spec.md
- Check type hints are complete
- Ensure error handling follows patterns
- Run single-file tests first
- **Explain every line before committing**

## Anti-Patterns to Reject

| Pattern | Problem | Correction |
|---------|---------|------------|
| God service | Single class doing everything | Decompose by responsibility |
| Anemic domain | Logic scattered in handlers | Encapsulate in domain objects |
| Shotgun surgery | One change requires many files | Consolidate related logic |
| N+1 queries | Loop that queries per item | Use joins or eager loading |
| Primitive obsession | Raw strings for domain concepts | Create value objects |

## Reference Implementations

When generating code, follow patterns from:
- FastAPI Full-Stack Template: `github.com/fastapi/full-stack-fastapi-template`
- FastAPI Best Practices: `github.com/zhanymkanov/fastapi-best-practices`
- Amazon Builders' Library for distributed systems patterns
