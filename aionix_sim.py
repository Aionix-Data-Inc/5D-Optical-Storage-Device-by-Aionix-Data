import yaml
import logging
from datetime import datetime
import yaml
import logging
import sys
import os
import hashlib
import json
import time
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
except ImportError:
    Cipher = None
    algorithms = None
    modes = None
    default_backend = None
    hashes = None
    ed25519 = None
    serialization = None
import yaml
import logging
import sys
import os
import hashlib
import json
import time
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
except ImportError:
    Cipher = None
    algorithms = None
    modes = None
    default_backend = None
    hashes = None
    ed25519 = None
    serialization = None


# Setup logging
logging.basicConfig(filename='aionix_sim.log', level=logging.INFO, format='%(asctime)s %(message)s')
# Setup audit trail logging
# Setup audit trail logging
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler('aionix_audit.log')
audit_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)

# Persistent key storage
KEY_STORE_FILE = 'aionix_keys.json'
def load_keys():
    if os.path.isfile(KEY_STORE_FILE):
        with open(KEY_STORE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_key(username, key):
    keys = load_keys()
    keys[username] = key.hex()
    with open(KEY_STORE_FILE, 'w') as f:
        json.dump(keys, f)
    audit_logger.info(f"KEY_SAVED user={username} key={key.hex()}")

def get_key(username):
    keys = load_keys()
    return bytes.fromhex(keys.get(username, '')) if username in keys else None

# Tamper detection
def file_hash(filepath):
    if not os.path.isfile(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


import stat
import smtplib
import requests
TAMPER_EVENTS_FILE = 'tamper_events.json'
WEBHOOK_URL = os.environ.get('AIONIX_WEBHOOK_URL')  # Set externally
SMTP_SERVER = os.environ.get('AIONIX_SMTP_SERVER')
SMTP_TO = os.environ.get('AIONIX_SMTP_TO', 'aionixdata@gmail.com')
tamper_history = {}

# External alerting and monitoring

def alert_external(event):
    # Always include alert emails in event for webhook
    emails = set()
    if 'email' in event:
        emails.add(event['email'])
    emails.add(SMTP_TO)
    # Only keep aionixdata@gmail.com as recipient
    emails.discard('aionidata@gmail.com')
    emails.add('aionixdata@gmail.com')
    event['emails'] = list(emails)

    # Always log to tamper_events.json, even if webhook/email fails
    events = []
    try:
        if os.path.isfile(TAMPER_EVENTS_FILE):
            with open(TAMPER_EVENTS_FILE, 'r') as f:
                events = json.load(f)
    except Exception:
        events = []
    events.append(event)
    try:
        with open(TAMPER_EVENTS_FILE, 'w') as f:
            json.dump(events, f)
    except Exception:
        pass

    # Webhook
    if WEBHOOK_URL:
        try:
            requests.post(WEBHOOK_URL, json=event, timeout=5)
        except Exception:
            pass
    # Email
    if SMTP_SERVER and SMTP_TO:
        try:
            with smtplib.SMTP(SMTP_SERVER) as s:
                s.sendmail('aionix@localhost', SMTP_TO, f"Subject: Tamper Alert\n\n{json.dumps(event)}")
        except Exception:
            pass

# Tamper checks

def check_file_deleted(filepath):
    if not os.path.isfile(filepath):
        msg = f"Tamper detected: {filepath} was deleted!"
        audit_logger.error(f"TAMPER_DETECTED file_deleted={filepath}")
        print(msg)
        alert_external({'type':'delete','file':filepath,'msg':msg,'ts':datetime.now().isoformat()})
        return True
    return False

def check_file_renamed(filepath):
    bak = filepath + '.bak'
    if not os.path.isfile(filepath) and os.path.isfile(bak):
        msg = f"Tamper detected: {filepath} was renamed to {bak}!"
        audit_logger.error(f"TAMPER_DETECTED file_renamed={filepath} to={bak}")
        print(msg)
        alert_external({'type':'rename','file':filepath,'to':bak,'msg':msg,'ts':datetime.now().isoformat()})
        return True
    return False

def check_file_permissions(filepath):
    if not os.path.isfile(filepath):
        return False
    st = os.stat(filepath)
    if st.st_mode & stat.S_IWOTH:
        msg = f"Tamper detected: {filepath} is world-writable!"
        audit_logger.error(f"TAMPER_DETECTED file_permission={filepath} mode={oct(st.st_mode)}")
        print(msg)
        alert_external({'type':'permission','file':filepath,'mode':oct(st.st_mode),'msg':msg,'ts':datetime.now().isoformat()})
        return True
    return False

def check_rapid_modifications(filepath):
    if not os.path.isfile(filepath):
        return False
    mtime = os.path.getmtime(filepath)
    now = time.time()
    history = tamper_history.get(filepath, [])
    history = [t for t in history if now - t < 10]
    history.append(mtime)
    tamper_history[filepath] = history
    if len(history) > 3:
        msg = f"Tamper detected: {filepath} modified {len(history)} times in 10 seconds!"
        audit_logger.error(f"TAMPER_DETECTED rapid_modification={filepath} count={len(history)}")
        print(msg)
        alert_external({'type':'rapid_mod','file':filepath,'count':len(history),'msg':msg,'ts':datetime.now().isoformat()})
        return True
    return False

def check_file_size(filepath, initial_size):
    if not os.path.isfile(filepath):
        return False
    size = os.path.getsize(filepath)
    if initial_size is not None and (size > initial_size * 2 or size < initial_size // 2):
        msg = f"Tamper detected: {filepath} size changed from {initial_size} to {size}!"
        audit_logger.error(f"TAMPER_DETECTED file_size={filepath} from={initial_size} to={size}")
        print(msg)
        alert_external({'type':'size','file':filepath,'from':initial_size,'to':size,'msg':msg,'ts':datetime.now().isoformat()})
        return True
    return False

def check_forbidden_keywords(filepath, keywords):
    if not os.path.isfile(filepath):
        return False
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        for kw in keywords:
            if kw in content:
                msg = f"Tamper detected: {filepath} contains forbidden keyword '{kw}'!"
                audit_logger.error(f"TAMPER_DETECTED file_keyword={filepath} keyword={kw}")
                print(msg)
                alert_external({'type':'keyword','file':filepath,'keyword':kw,'msg':msg,'ts':datetime.now().isoformat()})
                return True
    except Exception:
        pass
    return False

def check_tamper(filepath, expected_hash, ignore_if_written=False, initial_size=None, forbidden_keywords=None):
    if check_file_deleted(filepath):
        return True
    if check_file_renamed(filepath):
        return True
    if check_file_permissions(filepath):
        return True
    if check_rapid_modifications(filepath):
        return True
    if check_file_size(filepath, initial_size):
        return True
    if forbidden_keywords and check_forbidden_keywords(filepath, forbidden_keywords):
        return True
    current_hash = file_hash(filepath)
    if ignore_if_written and current_hash != expected_hash:
        mtime = os.path.getmtime(filepath)
        now = time.time()
        if now - mtime > 2:
            msg = f"Tamper detected in {filepath}! Expected {expected_hash}, got {current_hash}"
            audit_logger.error(f"TAMPER_DETECTED file={filepath} expected={expected_hash} actual={current_hash}")
            print(msg)
            alert_external({'type':'hash','file':filepath,'expected':expected_hash,'actual':current_hash,'msg':msg,'ts':datetime.now().isoformat()})
            return True
        return False
    elif current_hash != expected_hash:
        msg = f"Tamper detected in {filepath}! Expected {expected_hash}, got {current_hash}"
        audit_logger.error(f"TAMPER_DETECTED file={filepath} expected={expected_hash} actual={current_hash}")
        print(msg)
        alert_external({'type':'hash','file':filepath,'expected':expected_hash,'actual':current_hash,'msg':msg,'ts':datetime.now().isoformat()})
        return True
    return False

def load_policy(policy_path):
    try:
        with open(policy_path, 'r') as f:
            policy = yaml.safe_load(f)
        logging.info(f"Loaded policy: {policy.get('ruleset_name')}")
        return policy
    except Exception as e:
        logging.error(f"Failed to load policy file: {e}")
        sys.exit(1)

def load_data(data_path):
    try:
        with open(data_path, 'rb') as f:
            data = f.read()
        logging.info(f"Loaded data file: {data_path} ({len(data)} bytes)")
        return data
    except Exception as e:
        logging.error(f"Failed to load data file: {e}")
        sys.exit(1)



# Role management
class UserContext:
    def __init__(self, username, roles):
        self.username = username
        self.roles = set(roles)

    def has_role(self, role):
        return role in self.roles

def has_access(policy, required_role, user=None):
    # Check policy and user context for required role
    roles = set(policy.get('metadata', {}).get('roles', ['writer', 'reader']))
    if user:
        if not user.has_role(required_role):
            logging.error(f"Access denied for user {user.username} role: {required_role}")
            audit_logger.info(f"DENY user={user.username} role={required_role}")
            print(f"Access denied for user {user.username} role: {required_role}")
            sys.exit(1)
        audit_logger.info(f"ALLOW user={user.username} role={required_role}")
    elif required_role not in roles:
        logging.error(f"Access denied for role: {required_role}")
        audit_logger.info(f"DENY role={required_role}")
        print(f"Access denied for role: {required_role}")
        sys.exit(1)
    logging.info(f"Access granted for role: {required_role}")
    audit_logger.info(f"ALLOW role={required_role}")
    return True

def encrypt_chunk(chunk, key):
    if Cipher is None:
        # Fallback: reverse bytes
        return chunk[::-1]
    iv = b'\x00'*16
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(chunk) + encryptor.finalize()

def sign_data(data, private_key=None):
    if ed25519 is None:
        return b'SIMULATED_SIGNATURE'
    if private_key is None:
        private_key = ed25519.Ed25519PrivateKey.generate()
    signature = private_key.sign(data)
    return signature

def hash_data(data):
    return hashlib.sha256(data).hexdigest()


def writer_pipeline(data, policy, user=None):
    has_access(policy, 'writer', user)
    logging.info("Writer pipeline started")
    audit_logger.info(f"START writer_pipeline user={user.username if user else 'system'}")
    # Tamper detection: check audit log and key store
    audit_log_hash = file_hash('aionix_audit.log')
    key_store_hash = file_hash(KEY_STORE_FILE)
    audit_logger.info(f"AUDITLOG_HASH {audit_log_hash}")
    audit_logger.info(f"KEYSTORE_HASH {key_store_hash}")
    # 1. Ingest
    logging.info("Ingest: Received data of length %d", len(data))
    audit_logger.info(f"INGEST user={user.username if user else 'system'} datalen={len(data)}")
    # 2. Chunk
    chunk_size = 4096 if len(data) > 4096 else 512
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    logging.info(f"Chunked into {len(chunks)} chunks of size {chunk_size}")
    audit_logger.info(f"CHUNK user={user.username if user else 'system'} chunks={len(chunks)} size={chunk_size}")
    # 3. Encrypt (optional)
    encryption_enabled = any(r['id'] == 'ENCRYPT' and r['action'] == 'enable' for r in policy.get('rules', []))
    key = None
    if encryption_enabled:
        key = get_key(user.username)
        if not key:
            key = os.urandom(32)
            save_key(user.username, key)
        logging.info("Encrypt: AES-256 encryption applied to chunks")
        audit_logger.info(f"ENCRYPT user={user.username if user else 'system'} key={key.hex()}")
        chunks = [encrypt_chunk(c, key) for c in chunks]
        logging.info("Security: Encryption key used and stored persistently")
    # 4. ECC encode
    logging.info("ECC encode: Simulated LDPC + RS encoding")
    audit_logger.info(f"ECC user={user.username if user else 'system'}")
    # 5. Symbol mapping (θ, δ)
    logging.info("Symbol mapping: Mapped chunks to (θ, δ) symbols")
    audit_logger.info(f"SYMBOL_MAP user={user.username if user else 'system'}")
    # 6. 3D path planning
    logging.info("3D path planning: Planned voxel paths")
    audit_logger.info(f"PATH_PLAN user={user.username if user else 'system'}")
    # 7. Laser control
    logging.info("Laser control: Simulated femtosecond laser writing")
    audit_logger.info(f"LASER_WRITE user={user.username if user else 'system'}")
    # 8. Inline verify
    chunk_hashes = [hash_data(c) for c in chunks]
    logging.info(f"Inline verify: SHA-256 hashes computed for chunks: {chunk_hashes}")
    audit_logger.info(f"VERIFY user={user.username if user else 'system'} hashes={chunk_hashes}")
    # 9. Catalog & sign
    catalog_entry = b''.join(chunks)
    signature = sign_data(catalog_entry)
    logging.info(f"Catalog & sign: Entry signed with Ed25519 (simulated if unavailable). Signature: {signature.hex() if isinstance(signature, bytes) else signature}")
    audit_logger.info(f"CATALOG_SIGN user={user.username if user else 'system'} signature={signature.hex() if isinstance(signature, bytes) else signature}")
    logging.info("Writer pipeline completed")
    audit_logger.info(f"END writer_pipeline user={user.username if user else 'system'}")
    return True



def reader_pipeline(sensor_data, policy, user=None):
    has_access(policy, 'reader', user)
    logging.info("Reader pipeline started")
    audit_logger.info(f"START reader_pipeline user={user.username if user else 'system'}")
    # Tamper detection: check audit log and key store
    audit_log_hash = file_hash('aionix_audit.log')
    key_store_hash = file_hash(KEY_STORE_FILE)
    audit_logger.info(f"AUDITLOG_HASH {audit_log_hash}")
    audit_logger.info(f"KEYSTORE_HASH {key_store_hash}")
    # 1. Scan/acquire
    logging.info("Scan/acquire: Simulated sensor data of length %d", len(sensor_data))
    audit_logger.info(f"SCAN user={user.username if user else 'system'} datalen={len(sensor_data)}")
    # 2. Voxel reconstruction (θ, δ)
    logging.info("Voxel reconstruction: Extracted (θ, δ) parameters")
    audit_logger.info(f"VOXEL_RECON user={user.username if user else 'system'}")
    # 3. Demodulate
    logging.info("Demodulate: Converted symbols to digital data")
    audit_logger.info(f"DEMODULATE user={user.username if user else 'system'}")
    # 4. ECC decode
    logging.info("ECC decode: Simulated error correction")
    audit_logger.info(f"ECC user={user.username if user else 'system'}")
    # 5. Verify hashes/signatures
    data_hash = hash_data(sensor_data)
    logging.info(f"Verify: SHA-256 hash of data: {data_hash}")
    signature = sign_data(sensor_data)
    logging.info(f"Verify: Ed25519 signature (simulated if unavailable): {signature.hex() if isinstance(signature, bytes) else signature}")
    audit_logger.info(f"VERIFY user={user.username if user else 'system'} hash={data_hash} signature={signature.hex() if isinstance(signature, bytes) else signature}")
    # 6. Export & mount
    logging.info("Export & mount: Data exported and mounted")
    audit_logger.info(f"EXPORT user={user.username if user else 'system'}")
    logging.info("Reader pipeline completed")
    audit_logger.info(f"END reader_pipeline user={user.username if user else 'system'}")
    return True



def simulate_external_tamper(filepath):
    # Simulate external tampering by modifying the file
    with open(filepath, 'a') as f:
        f.write("\nTAMPER_TEST_LINE\n")
    print(f"Simulated external tampering in {filepath}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 aionix_sim.py <data_file> <policy_file> [username] [role1,role2,...] [--tamper <file>] ")
        sys.exit(1)
    data_file = sys.argv[1]
    policy_file = sys.argv[2]
    username = sys.argv[3] if len(sys.argv) > 3 else 'testuser'
    roles = sys.argv[4].split(',') if len(sys.argv) > 4 else ['writer', 'reader']
    tamper_file = None
    if len(sys.argv) > 5 and sys.argv[5] == '--tamper' and len(sys.argv) > 6:
        tamper_file = sys.argv[6]
    if not os.path.isfile(data_file):
        print(f"Data file not found: {data_file}")
        sys.exit(1)
    if not os.path.isfile(policy_file):
        print(f"Policy file not found: {policy_file}")
        sys.exit(1)
    data = load_data(data_file)
    policy = load_policy(policy_file)
    user = UserContext(username, roles)
    # Tamper detection: check data file
    data_hash = file_hash(data_file)
    audit_logger.info(f"DATAFILE_HASH {data_hash}")
    # Save initial hashes and sizes for later tamper check
    initial_audit_log_hash = file_hash('aionix_audit.log')
    initial_key_store_hash = file_hash(KEY_STORE_FILE)
    initial_data_hash = file_hash(data_file)
    initial_policy_hash = file_hash(policy_file)
    initial_audit_log_size = os.path.getsize('aionix_audit.log') if os.path.isfile('aionix_audit.log') else None
    initial_key_store_size = os.path.getsize(KEY_STORE_FILE) if os.path.isfile(KEY_STORE_FILE) else None
    initial_data_size = os.path.getsize(data_file) if os.path.isfile(data_file) else None
    initial_policy_size = os.path.getsize(policy_file) if os.path.isfile(policy_file) else None
    forbidden_keywords = ['FORBIDDEN', 'HACK', 'MALWARE']
    # Run pipelines
    writer_pipeline(data, policy, user)
    reader_pipeline(data, policy, user)
    # Optionally simulate external tampering
    if tamper_file:
        simulate_external_tamper(tamper_file)
    # Tamper check after pipelines (ignore changes if written by simulation)
    tampered_audit = check_tamper('aionix_audit.log', initial_audit_log_hash, ignore_if_written=True, initial_size=initial_audit_log_size, forbidden_keywords=forbidden_keywords)
    tampered_keys = check_tamper(KEY_STORE_FILE, initial_key_store_hash, ignore_if_written=True, initial_size=initial_key_store_size, forbidden_keywords=forbidden_keywords)
    tampered_data = check_tamper(data_file, initial_data_hash, ignore_if_written=True, initial_size=initial_data_size, forbidden_keywords=forbidden_keywords)
    tampered_policy = check_tamper(policy_file, initial_policy_hash, ignore_if_written=True, initial_size=initial_policy_size, forbidden_keywords=forbidden_keywords)
    if tampered_audit or tampered_keys or tampered_data or tampered_policy:
        audit_logger.error(f"TAMPER_ALERT user={user.username}")
        print("Tamper detected in one or more critical files!")
    logging.info("Simulation complete.")
    audit_logger.info(f"SIMULATION_COMPLETE user={user.username}")

if __name__ == "__main__":
    main()
