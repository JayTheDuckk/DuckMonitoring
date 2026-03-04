# Duck Monitoring Architecture Deep Dive

Understanding the architecture of Duck Monitoring is crucial for advanced deployments, custom integrations, or contributing to the codebase.

## 1. High-Level Topology

Duck Monitoring operates on a centralized Server-Agent model with agentless fallback capabilities.

```text
+-----------------------+       +------------------------+
|    Client Browser     |       |   Remote Monitored     |
|   (React Frontend)    |       |        Host            |
+-----------+-----------+       +-----------+------------+
            |                               |
            | HTTP / JWT                    | HTTP POST (JSON)
            v                               v
+--------------------------------------------------------+
|                     CORE SERVER                        |
|                                                        |
|  +-----------------+                +---------------+  |
|  | Nginx Webserver |                | Django Rest   |  |
|  | (Static Assets) |                | Framework API |  |
|  +-----------------+                +-------+-------+  |
|                                             |          |
|                                             |          |
|  +-----------------+                +-------+-------+  |
|  |   PostgreSQL    |<---------------| Alerting &    |  |
|  |   Database      |                | Eval Engine   |  |
|  +-----------------+                +---------------+  |
+--------------------------------------------------------+
```

## 2. Component breakdown

### 2.1. The Frontend (React SPA)
The frontend is a pure Single Page Application built with React.
- **Routing:** Handled entirely client-side via `react-router-dom`.
- **State Management:** Core contextual states (like Authentication) are managed via React Context (`AuthContext.js`). Local component states handle widget data.
- **API Communication:** All data is fetched asynchronously using Axios. Requests are intercepted to automatically append the JWT Bearer token required by the backend.

### 2.2. The Backend (Django REST Framework)
The backend acts as the definitive source of truth and the processing engine.
- **Stateless API:** It exposes REST endpoints. It does not render HTML templates (except for the built-in Django Admin, which is rarely used here).
- **Metric Ingestion:** The `/api/agents/submit/` endpoint is heavily optimized to accept large JSON payloads from agents.
- **Alert Evaluation:** When metrics are ingested, they are immediately cross-referenced against `AlertRule` models in the database to trigger state changes.
- **Agentless Polling:** Background tasks/views handle initiating ICMP pings or SNMP GET requests for unmanaged devices.

### 2.3. The Database Layer (PostgreSQL/SQLite)
- Relational mapping handles complex relationships seamlessly (e.g., A `Host` belongs to a `HostGroup`, and has many `Metrics`).
- **Time-Series Management:** Metrics are stored as discrete rows. Over time, these tables grow massive. A management command (`cleanup_metrics`) is utilized to prune stale historical data and maintain performance.

### 2.4. The Agent (Python)
The monitoring agent is incredibly lightweight by design to avoid impacting the performance of the host it is monitoring.
- **Dependencies:** It relies primarily on standard Python libraries plus `psutil` for OS-level metric extraction and `requests` for payload submission.
- **Execution:** It runs synchronously in a loop. If the core server is unreachable, the agent drops the current payload and simply attempts again on the next interval, preventing memory bloat from queueing.

## 3. Security Model

- **Authentication:** Users authenticate via standard username/password to receive a JWT access and refresh token. 
- **Agent Authorization:** Agents generate unique UUIDs upon installation. They authenticate to the API using their assigned UUID and optionally a shared global Auth Token defined in the main server configuration (`settings.py`).
- **Auditing:** Administrative actions (like deleting a host or modifying alert rules) generate records in the `AuditLog` table, viewable from the frontend settings.
