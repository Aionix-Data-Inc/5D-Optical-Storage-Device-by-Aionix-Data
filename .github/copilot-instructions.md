# 5D Optical Storage System - AI Coding Agent Instructions

## Architecture Overview

This is a **5D Optical Storage System** implementing ultra-secure, write-once archival storage with femtosecond laser technology. The system records data in nanostructured glass using 3D voxels with polarization information.

### Core Components & Data Flow

1. **SecurityManager** (`optical_storage/security.py`) - Cryptographic engine
   - AES-256-GCM with **per-chunk keys** derived from master key + chunk ID
   - Ed25519 digital signatures for manifests/TOCs
   - Dual hashing: SHA-256 + SHA-512 for all content

2. **DataIngestionEngine** (`optical_storage/storage.py`) - Chunking & deduplication
   - Configurable 1-8MB chunks with content-based deduplication
   - Supports files, tar/zip archives, and S3-like objects
   - Each chunk gets unique encryption key and integrity hashes

3. **OpticalStorage** (`optical_storage/core.py`) - Main orchestrator
   - Manages **Manifests** (digitally signed object collections)  
   - Generates **Table of Contents (TOC)** for physical disc organization
   - Handles manifest import/export and cross-reference validation

4. **ObjectStore** abstraction - Pluggable storage backends
   - `FileSystemObjectStore` for local development/testing
   - Designed for S3-compatible and custom backends

### Key Security Patterns

- **Per-chunk encryption**: Each chunk gets unique AES key via `generate_chunk_key(chunk_id)`
- **Deterministic keys**: Same chunk ID always produces same encryption key
- **Dual hashing**: Both SHA-256 and SHA-512 for future-proofing
- **Signature verification**: All manifests and TOCs are Ed25519 signed

### Development Workflows

#### Running the System
```bash
# Demo all features
python demo.py

# CLI operations
python cli.py --storage-path ./storage store-file document.pdf
python cli.py --storage-path ./storage stats --detailed
python cli.py --storage-path ./storage create-toc disc_001

# Run tests
python -m pytest tests/ -v
```

#### Key File Patterns

- **Chunking logic**: See `DataIngestionEngine.ingest_data()` in `storage.py`
- **Encryption flow**: `SecurityManager.encrypt_chunk()` → `ObjectStore.put_chunk()`
- **Manifest structure**: `Manifest.to_dict()` shows complete metadata format
- **CLI argument patterns**: `cli.py` demonstrates proper initialization order

### Security & Tamper Detection Framework

The system includes comprehensive tamper monitoring via `aionix_sim.py` and `execute_simulation.py`:

#### Tamper Detection Patterns
- **File integrity**: SHA-256 hash verification against expected baselines
- **Permission monitoring**: Detects world-writable files via `stat.S_IWOTH` checks  
- **Rapid modification detection**: Flags files modified >3 times in 10 seconds
- **Content scanning**: Searches for forbidden keywords (`FORBIDDEN`, `HACK`, `MALWARE`)
- **File existence**: Detects deleted/renamed critical files (audit logs, key stores)
- **Size anomalies**: Alerts on 2x size increases or 50% decreases

#### Security Event Logging
- **Audit trail**: `aionix_audit.log` with timestamped operations (ALLOW, INGEST, VERIFY, etc.)
- **Tamper events**: `tamper_events.json` with structured event data for external systems
- **External alerting**: SMTP/webhook integration via environment variables (`AIONIX_WEBHOOK_URL`, `AIONIX_SMTP_SERVER`)

#### Critical Monitored Files
- `aionix_audit.log` - Operation audit trail with hash verification
- `aionix_keys.json` - Persistent key storage with tamper detection
- `sample_policy.yaml` - Storage policies with ECC/thermal settings
- User data files - Content and metadata integrity verification

### Testing & Validation Framework

#### Core Testing Workflows
```bash
# Unit tests for all components
python -m pytest tests/ -v

# Full system simulation with tamper detection
python aionix_sim.py sample_data.txt sample_policy.yaml alice writer,reader,admin

# Comprehensive tamper scenario testing
python execute_simulation.py

# Execution logging with monitoring
python run_and_log.py <command> [args...]
```

#### Simulation Pipeline Architecture
The system implements **writer_pipeline** and **reader_pipeline** workflows:

**Writer Pipeline**: `INGEST → CHUNK → ECC → SYMBOL_MAP → PATH_PLAN → LASER_WRITE → VERIFY → CATALOG_SIGN`
**Reader Pipeline**: `SCAN → VOXEL_RECON → DEMODULATE → ECC → VERIFY → EXPORT`

Each pipeline stage logs to `aionix_audit.log` with user context and tamper detection checkpoints.

#### Automated Tamper Testing
`execute_simulation.py` systematically tests tamper scenarios:
- **File deletion**: Removes critical files and tests detection
- **Permission tampering**: Makes files world-writable 
- **Rapid modification**: Triggers >3 modifications in 10 seconds
- **Keyword injection**: Inserts `FORBIDDEN`, `HACK`, `MALWARE` into files
- **File renaming**: Moves files to `.bak` extensions

Each scenario runs against: `aionix_audit.log`, `aionix_keys.json`, `sample_data.txt`, `sample_policy.yaml`

#### Logging Architecture
- **`aionix_sim.log`** - General simulation operations
- **`aionix_audit.log`** - Security audit trail with hash verification
- **`execute_simulation.log`** - Tamper scenario test results
- **`execution_log.txt`** - Command execution monitoring via `run_and_log.py`
- **`tamper_events.json`** - Structured tamper events for external systems

### Critical Implementation Notes

1. **Always initialize SecurityManager before ObjectStore** - encryption depends on security context
2. **Manifest IDs are UUIDs** - use `str(uuid.uuid4())` for new manifests  
3. **Chunk size limits**: Default 2MB, configurable 1-8MB range for optimal encryption performance
4. **Error handling**: All cryptographic operations must handle `cryptography` exceptions
5. **Deduplication**: Content-based using SHA-256 hashes, enabled by default in CLI

### Extension Points

- Add new `ObjectStore` implementations by subclassing abstract base class
- Extend `Manifest` metadata fields while preserving signature compatibility  
- Add storage policies through YAML configuration (see `sample_policy.yaml`)
- Implement custom chunking strategies in `DataIngestionEngine`

When modifying cryptographic components, always verify with existing test cases and maintain backward compatibility for manifest/TOC formats.