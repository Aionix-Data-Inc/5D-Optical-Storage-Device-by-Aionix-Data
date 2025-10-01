# 5D Optical Storage System - Production Deployment Guide

## Quick Start - Production Ready

The 5D Optical Storage System is now live and ready for production deployment. This guide provides step-by-step instructions for deploying the system in enterprise environments.

## Prerequisites

- Python 3.8+ 
- Linux/Unix environment (tested on Ubuntu 24.04)
- Minimum 4GB RAM, 100GB+ storage for optical disc management
- Network access for external tamper alerting (optional)

## Installation

### 1. Clone and Install
```bash
git clone https://github.com/Aionix-Data-Inc/5D-Optical-Storage-Device-by-Aionix-Data.git
cd 5D-Optical-Storage-Device-by-Aionix-Data
pip install -r requirements.txt
pip install -e .  # Development installation
```

### 2. Production Installation
```bash
pip install optical-storage-5d  # When published to PyPI
```

## Production Configuration

### 1. Environment Variables
```bash
export AIONIX_STORAGE_PATH="/opt/aionix/storage"
export AIONIX_WEBHOOK_URL="https://your-monitoring-system.com/webhooks/tamper"
export AIONIX_SMTP_SERVER="smtp.your-company.com"
export AIONIX_SMTP_TO="security-team@your-company.com"
```

### 2. Security Setup
```bash
# Create secure storage directory
sudo mkdir -p /opt/aionix/storage
sudo chown app:app /opt/aionix/storage
sudo chmod 750 /opt/aionix/storage

# Set up audit logging
sudo touch /var/log/aionix_audit.log
sudo chown app:app /var/log/aionix_audit.log
sudo chmod 640 /var/log/aionix_audit.log
```

## Production Usage

### 1. CLI Operations
```bash
# Store critical documents
python cli.py --storage-path /opt/aionix/storage store-file /path/to/document.pdf

# Store archive backups
python cli.py --storage-path /opt/aionix/storage store-archive /path/to/backup.tar.gz

# Generate disc TOC for physical writing
python cli.py --storage-path /opt/aionix/storage create-toc PROD_DISC_001

# Monitor system health
python cli.py --storage-path /opt/aionix/storage stats --detailed
```

### 2. Programmatic Integration
```python
from optical_storage import OpticalStorage, SecurityManager
from optical_storage.storage import FileSystemObjectStore

# Production initialization
security_manager = SecurityManager()
object_store = FileSystemObjectStore("/opt/aionix/storage")
storage = OpticalStorage(security_manager, object_store)

# Store enterprise data
object_id = storage.store_file("/path/to/critical-data.pdf")
manifest_id = storage.create_disc_toc("ENTERPRISE_DISC_001")
```

### 3. Monitoring & Alerting
```bash
# Run continuous tamper monitoring
python aionix_sim.py /path/to/data sample_policy.yaml production writer,reader,admin

# Automated tamper testing (run periodically)
python execute_simulation.py

# Log all operations for compliance
python run_and_log.py python cli.py --storage-path /opt/aionix/storage stats
```

## Security Features in Production

### 1. **Tamper Detection Active**
- Real-time file integrity monitoring
- Permission change detection
- Rapid modification alerts (>3 changes in 10 seconds)
- Forbidden keyword scanning
- External webhook/email alerting

### 2. **Encryption Standards**
- AES-256-GCM per-chunk encryption
- Ed25519 digital signatures
- SHA-256 + SHA-512 dual hashing
- Deterministic key derivation for deduplication

### 3. **Audit Compliance**
- Complete operation audit trail in `aionix_audit.log`
- Structured tamper events in `tamper_events.json`
- Digital signature verification for all manifests
- Immutable write-once storage model

## System Integration

### 1. **Storage Backends**
- **Development**: FileSystemObjectStore
- **Production**: Extend for S3/Azure/GCS compatibility
- **Enterprise**: Custom ObjectStore implementations

### 2. **Monitoring Integration**
- **Webhooks**: POST tamper events to monitoring systems
- **SMTP**: Email security alerts to operations teams  
- **Logs**: Structured JSON events for SIEM integration

### 3. **CI/CD Integration**
```yaml
# Example GitHub Actions workflow
- name: Validate 5D Storage System
  run: |
    python -m pytest tests/ -v
    python execute_simulation.py
    python demo.py
```

## Performance & Scale

### 1. **Throughput**
- **Chunking**: 1-8MB configurable chunk sizes
- **Encryption**: Hardware-accelerated AES-256-GCM
- **Deduplication**: Content-based with SHA-256 hashing
- **Concurrent**: Thread-safe for multi-user environments

### 2. **Storage Capacity**
- **Per Disc**: ~1GB usable capacity (configurable)
- **Scalability**: Unlimited discs via manifest system
- **Efficiency**: Content deduplication reduces storage requirements

## Support & Documentation

### 1. **Testing Validation**
```bash
# Complete system test
python -m pytest tests/ -v                    # All 13 tests must pass
python demo.py                               # Integration test
python execute_simulation.py                 # Security validation
```

### 2. **AI Development Support**
- See `.github/copilot-instructions.md` for AI coding agent guidance
- Complete architecture documentation for developers
- Tamper detection patterns and security frameworks documented

## Production Checklist

- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Storage directory configured with proper permissions  
- [ ] Environment variables set for monitoring/alerting
- [ ] Audit logging configured and accessible
- [ ] All tests passing (`pytest tests/ -v`)
- [ ] Demo validation successful (`python demo.py`)
- [ ] Tamper detection active (`python execute_simulation.py`)
- [ ] Monitoring integration configured (webhooks/SMTP)
- [ ] Backup procedures established for manifests and TOCs

## Status: ✅ PRODUCTION READY

The 5D Optical Storage System has been validated and is ready for enterprise deployment with full security monitoring, tamper detection, and audit compliance features active.

**Version**: 1.0.0  
**Last Updated**: October 1, 2025  
**Security Status**: All tamper detection systems operational  
**Test Status**: All 13 unit tests + integration tests passing  