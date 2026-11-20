# ECHOME – Time Capsule Messaging System

## 1. Project Overview

ECHOME is a web application that allows users to create encrypted “time capsules” – messages (text or audio) that are securely stored and automatically delivered to a recipient’s email at a future date. The system uses blockchain technology to enforce the release time, IPFS for decentralized file storage, and a Celery task queue for background processing.

### Key Features

- **End‑to‑end encryption**: Files are encrypted client‑side using AES‑256‑CBC; the server never sees the plaintext.
- **Time‑locked delivery**: A smart contract stores the file’s CID and the unlock delay; delivery is triggered only after the specified time has passed.
- **Decentralized storage**: Files are stored on IPFS via Filebase.
- **Email notifications**: When a capsule expires, the decrypted file is emailed to the recipient.
- **Custom authentication**: Cookie‑based session management with brute‑force protection.

---

## 2. Technology Stack

| Component           | Technology / Service                               |
|---------------------|----------------------------------------------------|
| Backend Framework   | Django 4.2                                         |
| Database            | SQLite (development), PostgreSQL (production)      |
| Task Queue          | Celery + Redis (broker/backend)                    |
| Blockchain          | Ethereum (Sepolia testnet or SKALE)                |
| Smart Contract      | Solidity 0.8.x, deployed via `web3.py`             |
| IPFS Storage        | Filebase (S3‑compatible IPFS)                      |
| Frontend            | HTML, CSS, JavaScript (CryptoJS for encryption)    |
| Email               | Gmail SMTP (with SSL)                              |
| Logging             | Python `logging` module (console + file)           |
| Authentication      | Custom user model + custom session middleware      |

---

## 3. System Architecture

```mermaid
graph TD
    subgraph Client
        Browser[Browser]
        JS[JavaScript / CryptoJS]
    end

    subgraph Django Application
        Views[Views]
        Models[(Database)]
        Middleware[Custom Auth Middleware]
        Auth[Custom Authentication]
    end

    subgraph Background
        Celery[Celery Worker]
        Redis[(Redis)]
    end

    subgraph External
        IPFS[Filebase IPFS]
        Blockchain[Ethereum Smart Contract]
        SMTP[SMTP Server]
    end

    Browser -->|HTTP| Views
    JS -->|Encrypt & Upload| Views
    Views -->|Save| Models
    Views -->|Queue Task| Celery
    Celery -->|Upload| IPFS
    Celery -->|Store CID| Blockchain
    Celery -->|Check Expired| Blockchain
    Celery -->|Retrieve File| IPFS
    Celery -->|Send Email| SMTP
    Celery -->|Update| Models
    Middleware -->|Validate Session| Auth
    Auth -->|Query| Models

```

---

#  4. Workflows Diagrams 

---

## 4.1 Time Capsule Creation 

```mermaid
sequenceDiagram
    participant User
    participant Browser
    participant Django
    participant DB
    participant Celery
    participant IPFS
    participant Blockchain

    User->>Browser: Fill form (message, unlock time, email, password)
    Browser->>Browser: Encrypt file with AES-256-CBC
    Browser->>Django: POST /process_secure_upload/
    Django->>DB: Create TimeCapsule record (status=pending)
    Django->>DB: Save file bytes in File table
    Django->>Celery: Queue do_uploads(file_id, capsule_id)
    Django-->>Browser: Return success

    Celery->>DB: Get file bytes (File.get_and_delete)
    Celery->>IPFS: upload_and_get_cid(file_bytes)
    IPFS-->>Celery: CID
    Celery->>Blockchain: store_data(cid, unlock_time)
    Celery->>DB: Update capsule.cid and status

```

---
## 4.2  Time Capsule Delivery (Expiration Check)

```mermaid
sequenceDiagram
    participant CeleryBeat as Celery Beat
    participant CeleryWorker as Celery Worker
    participant Blockchain
    participant IPFS
    participant SMTP
    participant DB

    loop Every 60 seconds
        CeleryBeat->>CeleryWorker: run_send_notification
        CeleryWorker->>Blockchain: get_expired_data()
        Blockchain-->>CeleryWorker: List of expired CIDs
        alt No expired CIDs
            CeleryWorker-->>CeleryBeat: Done
        else For each CID
            CeleryWorker->>IPFS: get_file_by_cid(cid)
            IPFS-->>CeleryWorker: file bytes
            CeleryWorker->>IPFS: delete_file_by_cid(cid)
            CeleryWorker->>CeleryWorker: Decrypt file using capsule password
            CeleryWorker->>SMTP: send_email_with_attachment
            CeleryWorker->>DB: Update capsule.status = 'sent'
            CeleryWorker->>Blockchain: expire(cid)
        end
    end


```

---

## 4.3 User Authentication Flow

```mermaid

sequenceDiagram
    participant Browser
    participant Django
    participant Middleware
    participant DB

    Browser->>Django: POST /accounts/login/
    Django->>DB: Query User by email/username
    DB-->>Django: User object
    Django->>Django: Check password and frozen status
    alt Success
        Django->>DB: Create UserSession
        Django->>Browser: Set cookie XSESSIONID
        Browser->>Middleware: Subsequent request with cookie
        Middleware->>DB: Validate session token
        DB-->>Middleware: UserSession
        Middleware->>Django: Attach request.custom_user
    else Failure
        Django->>DB: Increment failed attempts, log attempt
        Django-->>Browser: Error message
    end


```

---
## 4.4 Blockchain Interaction Lifecycle

```mermaid 
graph TD
    A["User creates capsule"] --> B["Upload encrypted file to IPFS"]
    B --> C["Obtain CID from IPFS"]
    C --> D["Call contract.store(cid, unlock_time)"]
    D --> E["Transaction sent to blockchain"]
    E --> F["Transaction mined and confirmed"]
    F --> G["Wait for unlock time to pass"]
    G --> H["Celery periodic task calls contract.getExpired()"]
    H --> I["Contract returns list of expired CIDs"]
    I --> J["For each expired CID, retrieve file from IPFS"]
    J --> K["Decrypt file using stored password"]
    K --> L["Send email with decrypted file to recipient"]
    L --> M["Update capsule status to 'sent' in database"]
    M --> N["Call contract.expire(cid) to remove from list"]
    N --> O["Delete file from IPFS to free storage"]
```

---

# Database Models (ER Diagram)

```mermaid

erDiagram
    Users ||--o{ TimeCapsule : creates
    Users ||--o{ UserSession : owns
    Users ||--o{ failedLoginAttempt : has
    ScheduledTaskLog ||--|| "Celery Task" : logs

    Users {
        int id PK
        string username UK
        string email UK
        string full_name
        string password_hash
        bool is_active
        datetime created_at
        int failedLoginAttempts
        datetime freezed_till
        string user_type
    }

    UserSession {
        int id PK
        int user_id FK
        string session_key
        string device
        string ip
        string status
        datetime created_at
        datetime expires
    }

    failedLoginAttempt {
        int id PK
        int user_id FK
        string ip_address
        string user_agent
        datetime timestamp
    }

    TimeCapsule {
        int id PK
        int user_id FK
        string email
        string cid
        string decryption_pass
        datetime storage_time
        string status
        int unlock_time
        string file_ext
        string file_mime
    }

    File {
        int id PK
        binary file_data
    }

    ScheduledTaskLog {
        int id PK
        string task_name
        string status
        datetime started_at
        datetime completed_at
        text details
    }

```
---


















