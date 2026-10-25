# RepoDefense: System Architecture

## 1. Project North Star

> **Product:** RepoDefense  
> **Tagline:** "Prove that you understand — and can defend — the software you built."  
> **Core Loop:** Evidence → Claim → Defense → Stress Test → Evaluation → Mentor → Re-test

---

## 2. Architecture Overview

RepoDefense is designed as a **Modular Monolith**. This architectural choice prioritizes developer velocity, ease of deployment, and simplicity while maintaining strict internal boundaries to allow future extraction of services if strictly necessary. 

### Rationale
- **No Microservices:** The system operates in a single repository with a unified deployment model. Network boundaries between internal components introduce latency, point of failure, and operational overhead that RepoDefense does not need.
- **Single Database Strategy:** We use PostgreSQL 17 for both relational data (users, sessions, claims) and vector data (pgvector). This eliminates the need to synchronize data between a relational database and a separate vector database, significantly reducing complexity.
- **Deterministic First, AI Second:** We rely on deterministic parsers (Tree-sitter AST, git history) to extract ground truth. LLMs are used only for reasoning over this verified evidence. Code execution is strictly prohibited.

---

## 3. High-Level System Architecture (Diagram 1)

```mermaid
flowchart TD
    subgraph "Client Tier"
        Browser["User Browser"]
    end

    subgraph "Frontend (Vercel)"
        NextJS["Next.js 15 App Router\n(TypeScript, shadcn/ui, Tailwind)"]
    end

    subgraph "Backend (Render)"
        FastAPI["FastAPI Backend\n(Python 3.12+)"]
        ARQ["ARQ Workers\n(Async Background Jobs)"]
    end

    subgraph "Managed Services"
        Supabase["Supabase\n(PostgreSQL 17 + pgvector)"]
        SupabaseAuth["Supabase Auth"]
        Upstash["Upstash\n(Redis Cache & Message Broker)"]
    end

    subgraph "External Integrations"
        GitHub["GitHub API\n(REST API)"]
        LLM["LiteLLM -> FreeLLMAPI\n(OpenAI Compatible)"]
    end

    %% Connections
    Browser <-->|HTTP/HTTPS| NextJS
    NextJS <-->|REST API| FastAPI
    NextJS <-->|JWT Auth| SupabaseAuth
    
    FastAPI <-->|SQLAlchemy/asyncpg| Supabase
    FastAPI <-->|Redis Protocol| Upstash
    FastAPI -->|Enqueue Jobs| ARQ
    
    ARQ <-->|Process Jobs| Upstash
    ARQ <-->|Read/Write| Supabase
    
    FastAPI <-->|REST API| GitHub
    ARQ <-->|REST API| GitHub
    
    FastAPI <-->|HTTP| LLM
    ARQ <-->|HTTP| LLM
```

### Component Responsibilities:
- **Next.js 15 (Frontend):** Manages user interfaces, dashboards, and defense session interactions. Handles client-side routing and server-side rendering for optimal performance.
- **FastAPI (Backend API):** The core control plane. Handles HTTP requests from the frontend, orchestrates business logic, manages authentication checks, and coordinates immediate LLM interactions.
- **ARQ (Background Jobs):** Async-native background workers built on Redis. Processes heavy, long-running tasks like repository ingestion, AST parsing, embedding generation, and report aggregation.
- **Supabase (Database + Auth):** Stores all relational schema data, vector embeddings (via pgvector), and manages user authentication (GitHub OAuth).
- **Upstash (Redis):** Acts as the message broker for ARQ and as a high-performance caching layer for rate-limiting and frequently accessed data.
- **FreeLLMAPI (via LiteLLM):** The abstraction layer and provider for LLM inference (used for defense question generation, evaluation, and claim verification).

---

## 4. Backend Module Architecture

The FastAPI backend enforces strict directory and module boundaries. 

```mermaid
flowchart LR
    api["api/ (HTTP Handlers)"]
    services["services/ (Business Logic)"]
    analyzers["analyzers/ (Code Analysis)"]
    ai["ai/ (LLM Interaction)"]
    workers["workers/ (ARQ Jobs)"]
    security["security/"]
    models["models/ (SQLAlchemy)"]
    schemas["schemas/ (Pydantic)"]
    core["core/ (Config & Middleware)"]

    api --> services
    api --> schemas
    api --> security
    api --> core

    services --> analyzers
    services --> ai
    services --> models
    services --> schemas
    
    workers --> services
    workers --> analyzers
    workers --> ai

    ai --> schemas
    analyzers --> schemas
```

### Module Boundaries & Dependency Rules
- `api/`: Only defines routes and request/response validation. Must not contain business logic. Injects dependencies and calls `services/`.
- `services/`: The orchestration layer. Coordinates database calls, triggers `analyzers/`, and utilizes `ai/`. 
- `analyzers/`: Deterministic logic pipeline. Contains `file_scanner`, `language_detector`, `ast_parser` (Tree-sitter), and `git_analyzer`. Never calls the database directly.
- `ai/`: Contains `llm_client` (LiteLLM wrapper), `prompts/`, `rag/`, `evaluator`, and the defense `interviewer` state machine.
- `workers/`: Background job definitions. They act similarly to API routes but are invoked via Redis. They compose logic from `services/` and `analyzers/`.
- `security/`: Middleware for sanitization, dependency checking, and secret detection.
- `models/`: SQLAlchemy ORM classes. No business logic.
- `schemas/`: Pydantic models for validation. Used across all modules.
- `core/`: Application settings, logging configuration (structlog), database connection pools, and Sentry setup.

---

## 5. Repository Ingestion Pipeline (Diagram 2)

```mermaid
flowchart TD
    Start["GitHub URL Input"] --> Val["URL Validation & Security Check"]
    Val --> Clone["Shallow Git Clone (--depth=1)"]
    Clone --> SizeVal["Size & File Count Validation"]
    SizeVal --> Filter["File Extension Filter (whitelist)"]
    Filter --> Secret["Secret Detection & Redaction"]
    
    Secret --> ParallelStart{"Parallel Processing Strategy"}
    
    ParallelStart --> FS["File Scanner (tree, sizes, types)"]
    ParallelStart --> LD["Language Detection"]
    ParallelStart --> AST["Tree-sitter AST Parsing"]
    ParallelStart --> Config["Config File Analysis"]
    ParallelStart --> Git["Git History Analysis"]
    ParallelStart --> Dep["Dependency File Parsing"]

    AST --> AST_F["Function Extraction"]
    AST --> AST_C["Class Extraction"]
    AST --> AST_I["Import/Dependency Extraction"]
    AST --> AST_E["Endpoint Detection"]

    Git --> Git_C["Commit Records"]
    Git --> Git_Auth["Contributor Analysis"]
    Git --> Git_Own["File Ownership Mapping"]

    %% Re-join
    FS & LD & AST_F & AST_C & AST_I & AST_E & Config & Git_C & Git_Auth & Git_Own & Dep --> LLMStart{"LLM-Assisted Steps (Sequential)"}

    LLMStart --> L1["File Summaries (batched)"]
    L1 --> L2["Project Summary"]
    L2 --> L3["Architecture Detection"]
    L3 --> L4["Evidence Extraction"]

    L4 --> EmbedStart{"Embedding Generation (all-MiniLM-L6-v2)"}

    EmbedStart --> E1["Code Chunk Embeddings (function/class)"]
    EmbedStart --> E2["File Summary Embeddings"]
    EmbedStart --> E3["Project Summary Embedding"]

    E1 & E2 & E3 --> DBStore["Store to PostgreSQL + pgvector"]
    DBStore --> StatusUpdate["Update Project Status -> Ready"]
```

### Rationale & Design
- **Shallow Clone:** `git clone --depth=1` avoids downloading years of irrelevant history, vastly improving speed and limiting malicious payload depth.
- **Deterministic vs LLM:** We strictly extract relationships, dependencies, and structure using Tree-sitter (deterministic). LLMs are only used in the subsequent aggregation phase for generating summaries and architecture insights.
- **Parallelization:** I/O heavy operations and deterministic parsing run in parallel using asyncio tasks within the ARQ worker.
- **Error Handling:** If a single file fails parsing, it is logged and skipped. If core dependencies (e.g., `package.json`) fail, the ingestion process is marked as degraded but proceeds.
- **Estimated Time:** A typical repository (100 files, ~15k LOC) takes < 2 minutes to ingest.

---

## 6. AI/RAG Pipeline (Diagram 3)

```mermaid
flowchart TD
    UserQ["User Query / Question Context"] --> QAnalyze["Query Analysis"]
    QAnalyze --> Filter["Metadata Filter Construction"]
    
    Filter --> ParallelRetrieve{"Parallel Retrieval"}
    ParallelRetrieve --> Semantic["pgvector Similarity Search (semantic)"]
    ParallelRetrieve --> Symbol["Symbol Search (exact match)"]
    ParallelRetrieve --> Keyword["File Path Search (keyword)"]
    
    Semantic & Symbol & Keyword --> Merge["Result Merging & Re-ranking"]
    Merge --> Context["Context Assembly (Token Budgeting)"]
    
    Context --> Prompt{"Prompt Construction"}
    Prompt --> P1["System Prompt (role + instructions)"]
    Prompt --> P2["Project Context (summary + arch)"]
    Prompt --> P3["Retrieved Evidence (citations)"]
    Prompt --> P4["Task-Specific Instructions"]
    
    P1 & P2 & P3 & P4 --> LLMCall["LLM Call (LiteLLM)"]
    LLMCall --> Parse["Response Parsing (Pydantic validation)"]
    Parse --> EvAttach["Evidence Attachment"]
    EvAttach --> Output["Final Output"]
```

### Context Window Budgeting (~4800 tokens max to fit safely in standard 8K contexts)
- **System prompt:** ~500 tokens
- **Project summary:** ~500 tokens
- **Retrieved evidence:** ~2000 tokens (strict crop based on relevance score)
- **Conversation history:** ~1000 tokens (rolling window)
- **Task instructions:** ~300 tokens
- **Response budget:** ~500 tokens

---

## 7. Defense Session Flow (Diagram 4)

```mermaid
stateDiagram-v2
    [*] --> INIT_SESSION
    INIT_SESSION --> GENERATE_FIRST_QUESTION
    GENERATE_FIRST_QUESTION --> AWAITING_ANSWER
    
    AWAITING_ANSWER --> EVALUATE_ANSWER: User Submits Answer
    
    state EVALUATE_ANSWER {
        [*] --> Assess
        Assess --> NEEDS_PUSHBACK?
    }
    
    EVALUATE_ANSWER --> GENERATE_PUSHBACK: Yes (Under Limit)
    GENERATE_PUSHBACK --> AWAITING_ANSWER
    
    EVALUATE_ANSWER --> UPDATE_COVERAGE: No (or Max Pushbacks Reached)
    UPDATE_COVERAGE --> CHECK_COMPLETION
    
    state CHECK_COMPLETION {
        [*] --> Complete?
    }
    
    CHECK_COMPLETION --> GENERATE_REPORT: Yes (Met Criteria)
    GENERATE_REPORT --> SESSION_COMPLETE
    SESSION_COMPLETE --> [*]
    
    CHECK_COMPLETION --> SELECT_NEXT_TOPIC: No
    SELECT_NEXT_TOPIC --> GENERATE_QUESTION
    GENERATE_QUESTION --> AWAITING_ANSWER
```

### Algorithm Details
- **Topic Selection:** Prioritizes un-defended architectural components first, followed by historically weak knowledge areas.
- **Pushback Limit:** A maximum of 2 pushbacks per topic to prevent the LLM from trapping the user in an infinite loop.
- **Completion Criteria:** A session ends when a minimum of 10 questions are answered, all core project topics are covered, or the user manually concludes it.
- **Score Aggregation:** Weighted average of deterministic confidence (from Code/Git) and LLM-evaluated confidence.

---

## 8. Claim Verification Flow (Diagram 5)

```mermaid
flowchart TD
    Resume["Resume Text"] --> Ext["LLM Claim Extraction (structured output)"]
    Ext --> Norm["Claim Normalization"]
    
    Norm --> Loop{"For Each Claim"}
    
    Loop --> TClaim["Technology Claim?"]
    TClaim --> TCheck["Check Dependencies + Imports + Config"]
    
    Loop --> AClaim["Architecture Claim?"]
    AClaim --> ACheck["Check Architecture Analysis + File Structure"]
    
    Loop --> FClaim["Feature Claim?"]
    FClaim --> FCheck["Semantic Search + Symbol Search"]
    
    Loop --> CClaim["Contribution Claim?"]
    CClaim --> CCheck["Git History Analysis"]
    
    Loop --> PClaim["Performance Claim?"]
    PClaim --> PCheck["Mark as Unverifiable (no runtime data)"]
    
    TCheck & ACheck & FCheck & CCheck & PCheck --> Score["Evidence Scoring (0-1 confidence)"]
    
    Score --> Status{"Status Assignment"}
    Status --> S1[">= 0.8: Verified"]
    Status --> S2["0.4 - 0.8: Partially Supported"]
    Status --> S3["0.1 - 0.4: Unsupported"]
    Status --> S4["< 0.1: Unverifiable"]
    
    S1 & S2 & S3 & S4 --> Store["Store ClaimEvidenceLinks"]
```

---

## 9. Ownership Analysis (Diagram 6)

```mermaid
flowchart TD
    Git["Git History"] --> Ext["Contributor Extraction"]
    Ext --> PerUser{"Per-Contributor Analysis"}
    
    PerUser --> U1["Commit Frequency"]
    PerUser --> U2["Files Touched"]
    PerUser --> U3["Code Areas (frontend/backend/etc)"]
    PerUser --> U4["Temporal Pattern (activity timeline)"]
    PerUser --> U5["PR Authorship"]
    
    U1 & U2 & U3 & U4 & U5 --> Heatmap["Ownership Heatmap (contributor x code area)"]
    Heatmap --> Compare["Comparison with User Claims"]
    Compare --> QGen["Generate Ownership-Specific Questions"]
```

### Explicit Limitations
- **Cannot Detect Pair Programming:** Only the recorded commit author is verified.
- **Cannot Detect Dictated Code:** Copied/pasted or AI-generated code attributed to a user cannot be deterministically proven false by history alone (this is why the defense session exists).
- **Volume ≠ Quality:** Commit counts do not reflect code complexity or quality.
- **Squashed/Rewritten History:** Squashed PRs or force-pushes mask granular history.

---

## 10. PR/Commit Defense (Diagram 7)

```mermaid
flowchart TD
    Select["PR/Commit Selection"] --> Fetch["Fetch Diff"]
    Fetch --> Ident["Identify Changed Files"]
    Ident --> Map["Map to Project Architecture"]
    
    Map --> Analyze{"Analyze Changes"}
    Analyze --> A1["What changed (deterministic diff analysis)"]
    Analyze --> A2["What could break (LLM reasoning w/ context)"]
    Analyze --> A3["New dependencies introduced"]
    Analyze --> A4["Security implications"]
    Analyze --> A5["Testing implications"]
    
    A1 & A2 & A3 & A4 & A5 --> GenQ["Generate Defense Questions"]
    GenQ --> DefSession["Defense Session (State Machine)"]
```

---

## 11. Incident Simulation (Diagram 8)

```mermaid
flowchart TD
    Arch["Project Architecture Analysis"] --> Identify{"Identify Components"}
    Identify --> C1["Database(s)"]
    Identify --> C2["Cache layer"]
    Identify --> C3["External APIs"]
    Identify --> C4["Auth service"]
    Identify --> C5["File storage"]
    Identify --> C6["ML/AI services"]
    
    C1 & C2 & C3 & C4 & C5 & C6 --> FailGen{"Generate Failure Scenarios"}
    FailGen --> F1["Component unavailable"]
    FailGen --> F2["Latency spike"]
    FailGen --> F3["Data corruption"]
    FailGen --> F4["Traffic surge"]
    FailGen --> F5["Dependency failure"]
    
    F1 & F2 & F3 & F4 & F5 --> Custom["Customize to Project\n(e.g., 'Your PostgreSQL instance...' not 'A database...')"]
    Custom --> Present["Present Scenario"]
    Present --> Eval["Evaluate Response (rubric-based)"]
```

---

## 12. Mentor/Retesting Loop (Diagram 9)

```mermaid
flowchart TD
    Weak["Weakness Identified"] --> Select["User Selects 'Teach Me'"]
    Select --> Retrieve["Retrieve Relevant Code from User's Project"]
    
    Retrieve --> ContentGen{"Generate Teaching Content"}
    ContentGen --> G1["Concept Explanation"]
    ContentGen --> G2["How It Applies to Their Code"]
    ContentGen --> G3["What Best Practice Looks Like"]
    
    G1 & G2 & G3 --> Mini["Mini Challenge\n(Project-specific question)"]
    Mini --> Ans["User Answers"]
    Ans --> Eval["Evaluate"]
    
    Eval --> Check{"Check Improvement"}
    Check --> |"Still Weak"| Deep["Deeper Teaching"]
    Check --> |"Improved"| Mark["Mark Progress / Update Weakness Score"]
    
    Deep --> ContentGen
```

---

## 13. Deployment Architecture (Diagram 10)

```mermaid
flowchart TD
    Dev["Developer"] -->|Push| GH["GitHub Repository"]
    GH -->|Webhook| CI["GitHub Actions CI/CD"]
    
    CI -->|Build & Deploy| Vercel["Frontend Deploy to Vercel"]
    CI -->|Build Docker & Deploy| Render["Backend Deploy to Render"]
    
    subgraph "Production Environment"
        Users["User Browser"]
        
        subgraph "Vercel"
            NextJS_Prod["Next.js SSR/RSC (CDN)"]
        end
        
        subgraph "Render (Free Tier)"
            FastAPI_Prod["FastAPI App Server"]
            ARQ_Worker["ARQ Worker Process"]
        end
        
        subgraph "Supabase"
            DB_Prod["PostgreSQL + pgvector\nAuth + Storage"]
        end
        
        subgraph "Upstash"
            Redis_Prod["Serverless Redis"]
        end
        
        subgraph "External Providers"
            LLM_API["FreeLLMAPI"]
            GH_API["GitHub API"]
        end
        
        Users -->|HTTPS| NextJS_Prod
        NextJS_Prod -->|HTTPS/REST| FastAPI_Prod
        FastAPI_Prod --> DB_Prod
        FastAPI_Prod --> Redis_Prod
        ARQ_Worker <--> Redis_Prod
        ARQ_Worker <--> DB_Prod
        FastAPI_Prod --> LLM_API
        FastAPI_Prod --> GH_API
    end
```

### Deployment Strategy
- **CI/CD:** Handled via GitHub Actions. Ensures passing tests, linting, and type checking before deployment.
- **Environment Management:** Environment variables are strictly injected via Vercel and Render dashboards.
- **Database Migrations:** Managed strictly via Alembic. The CI pipeline executes `alembic upgrade head` during the backend deployment phase.
- **Zero-Downtime:** Vercel handles frontend atomic deployments natively. Render rolling deploys update the FastAPI containers iteratively.
- **Cost Analysis (Free Tiers):** Vercel (Hobby), Render (Free Web Service + Background Worker hack/shared instance), Supabase (Free tier PostgreSQL + Auth), Upstash (Serverless Redis 10k requests/day), FreeLLMAPI (free tier). Code embeddings are processed locally via `sentence-transformers`, avoiding API costs.

---

## 14. Data Flow Architecture

1. **Intake:** User authorizes via Supabase Auth (GitHub OAuth) and submits a repository URL.
2. **Ingestion & Sync:** Frontend sends repo URL to Backend. Backend enqueues ARQ job and responds with 202 Accepted.
3. **Processing:** ARQ worker pulls the repository, executes AST extraction and Git history parsing, runs LLM batch jobs for summary generation, maps vectors, and updates status in Supabase.
4. **Session Init:** User initiates a defense session. Frontend requests an initialized state. Backend uses LiteLLM to analyze vectors, constructs the first question, and returns it.
5. **Interactive Defense:** User submits an answer. Backend evaluates the payload against strict rubrics, updates the pgvector session context, and generates the next node in the session graph.
6. **Reporting:** Once complete, ARQ job compiles a summary report of strengths, weaknesses, and a final grade.

---

## 15. Security Architecture

```mermaid
flowchart LR
    subgraph "Untrusted Zone"
        GH_Repos["GitHub Repos"]
        UserIn["User Input (Answers, Configs)"]
    end
    
    subgraph "Security Boundary"
        Val["Validation & Sanitization"]
        Size["Size Limits & Filters"]
    end
    
    subgraph "Processing Zone (NO EXECUTION)"
        Parser["Tree-sitter AST Parser"]
        Worker["ARQ Worker"]
    end
    
    subgraph "Storage Zone"
        DB["PostgreSQL (Encrypted at rest)"]
    end
    
    subgraph "AI Zone"
        LLM["LLM Calls (Sanitized Data)"]
    end
    
    subgraph "Output Zone"
        Report["Reports & Questions"]
    end
    
    GH_Repos --> Val
    UserIn --> Val
    Val --> Size
    Size --> Parser
    Parser --> Worker
    Worker --> DB
    Worker --> LLM
    LLM --> Report
```

### Trust Boundaries
- **No Code Execution:** RepoDefense parses code via Tree-sitter. It *never* runs `eval()`, `exec()`, or executes user tests/scripts. This prevents RCE completely.
- **Data Redaction:** Potential secrets (API keys, passwords) are filtered *before* being sent to the LLM or stored in pgvector.

---

## 16. Component Communication

- **Synchronous (REST API):** Used for lightweight CRUD, authentication checks, fetching session states, and simple frontend-to-backend commands.
- **Asynchronous (ARQ / Redis):** Used for all heavy processing: cloning repos, embedding generation, deep git log analysis, and compiling the final defense reports.
- **Direct Function Calls:** Internal FastAPI routing ensures modules like `services/` and `analyzers/` communicate natively in Python without network boundaries.

---

## 17. Scalability Path

As RepoDefense grows beyond the free tier, the Modular Monolith allows horizontal scaling:
- **Phase 1 (Current):** Single Render instance running FastAPI, utilizing `asyncio.create_task` for background tasks or a co-located lightweight ARQ worker process.
- **Phase 2:** Move the ARQ worker to a dedicated Render Background Worker instance to isolate CPU-intensive operations (AST parsing, local embedding generation) from HTTP traffic.
- **Phase 3:** Scale out multiple ARQ worker instances listening to the same Upstash Redis queue. Upgrade Supabase to a paid tier to support high concurrency pgvector reads.
- **Phase 4:** If strictly required by team size or domain isolation, split the ingestion pipeline and the defense session engine into separate services (microservices), though the monolith will likely suffice up to millions of users due to stateless design.
