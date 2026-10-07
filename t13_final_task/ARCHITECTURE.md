# T13 Architecture: How Everything Connects

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  WINDOWS HOST  (C:\Users\Anton_Fiadotau\...)                                    ║
║                                                                                  ║
║   Browser  ──── http://localhost:8080 ────► python -m http.server               ║
║      │                                      (serves index.html)                 ║
║      │                                                                           ║
║      └──── HTTP POST :8011/conversations/{id}/chat                              ║
║                  │                                                               ║
║  ┌───────────────────────────────────────────────────────────────────────────┐  ║
║  │  WSL2  (virtual Linux kernel, mounted at /mnt/c/...)                      │  ║
║  │                                                                            │  ║
║  │   app.py  (FastAPI on :8011, PYTHONPATH=.)                                │  ║
║  │      │                                                                     │  ║
║  │      ├── redis.Redis() ──────────────────────── localhost:6379 ──────┐    │  ║
║  │      │                                                                │    │  ║
║  │      ├── HttpMcpClient ─────────────────────── localhost:8005/mcp ───┤    │  ║
║  │      │                                                                │    │  ║
║  │      └── StdioMcpClient ──── docker run khshanovskyi/ddg-mcp-server ─┤    │  ║
║  │                               (spawns container via Docker socket)   │    │  ║
║  │                                                                       │    │  ║
║  │  ┌─────────────────────────────────────────────────────────────────┐ │    │  ║
║  │  │  DOCKER ENGINE  (Linux daemon inside WSL2)                      │ │    │  ║
║  │  │                                                                  │ │    │  ║
║  │  │  ┌──────────────────────────────────────────────────────────┐   │ │    │  ║
║  │  │  │  DOCKER NETWORK: t13_final_task_default  (bridge)        │   │ │    │  ║
║  │  │  │                                                           │   │ │    │  ║
║  │  │  │  ┌─────────────────────┐   internal DNS                  │   │ │    │  ║
║  │  │  │  │  userservice        │◄─── "userservice:8000" ──────┐  │   │ │    │  ║
║  │  │  │  │  :8000 (internal)   │                              │  │   │ │    │  ║
║  │  │  │  │  :8041 (host)  ◄────┼── host.docker.internal:8041  │  │   │ │    │  ║
║  │  │  │  │                     │   (BROKEN in WSL — no DNS)   │  │   │ │    │  ║
║  │  │  │  │  image: mockuser..  │                              │  │   │ │    │  ║
║  │  │  │  │  volume: ./data ───►│── /app/data                  │  │   │ │    │  ║
║  │  │  │  └─────────────────────┘                              │  │   │ │    │  ║
║  │  │  │                                                        │  │   │ │    │  ║
║  │  │  │  ┌─────────────────────┐                              │  │   │ │    │  ║
║  │  │  │  │  ums-mcp-server     │── USERS_MANAGEMENT_SERVICE ──┘  │   │ │    │  ║
║  │  │  │  │  :8005 (internal)   │   _URL=http://userservice:8000  │   │ │    │  ║
║  │  │  │  │  :8005 (host)  ◄────┼──────────────────────────────── ┼───┘ │    │  ║
║  │  │  │  │                     │                                  │     │    │  ║
║  │  │  │  │  image: ums-mcp-..  │                                  │     │    │  ║
║  │  │  │  │  volume: ./data ───►│── /app/data                      │     │    │  ║
║  │  │  │  └─────────────────────┘                                  │     │    │  ║
║  │  │  │                                                            │     │    │  ║
║  │  │  │  ┌─────────────────────┐                                  │     │    │  ║
║  │  │  │  │  redis-ums          │                                  │     │    │  ║
║  │  │  │  │  :6379 (internal)   │                                  │     │    │  ║
║  │  │  │  │  :6379 (host)  ◄────┼──────────────────────────────────┼─────┘    │  ║
║  │  │  │  │                     │                                  │          │  ║
║  │  │  │  │  image: redis:7.2   │                                  │          │  ║
║  │  │  │  │  (no volume = data  │                                  │          │  ║
║  │  │  │  │   lives in container│                                  │          │  ║
║  │  │  │  │   memory only)      │                                  │          │  ║
║  │  │  │  └─────────────────────┘                                  │          │  ║
║  │  │  │                                                            │          │  ║
║  │  │  │  ┌─────────────────────┐                                  │          │  ║
║  │  │  │  │  redis-insight      │                                  │          │  ║
║  │  │  │  │  :5540 (internal)   │  GUI for inspecting Redis data   │          │  ║
║  │  │  │  │  :6380 (host)       │  → open http://localhost:6380    │          │  ║
║  │  │  │  └─────────────────────┘                                  │          │  ║
║  │  │  └──────────────────────────────────────────────────────────────         │  ║
║  │  │                                                                           │  ║
║  │  │  VOLUME (bind mount): t13_final_task/data/  ◄──► /app/data               │  ║
║  │  │  (shared folder on disk, visible to both userservice & ums-mcp-server)   │  ║
║  │  └───────────────────────────────────────────────────────────────────────┘  ║
║  └───────────────────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## Key Concepts

### WSL2
A full Linux kernel running as a lightweight VM inside Windows.
Your Python app runs here (not on Windows directly), so paths are `/mnt/c/...` instead of `C:\...`.
Docker Engine also runs inside WSL2 as a native Linux process.

### Docker Network (bridge)
Compose creates a private virtual network for all services in the same `docker-compose.yml`.
Inside that network, each container is reachable **by its service name** (e.g. `userservice`, `redis-ums`).
From outside (host/WSL), you reach them via mapped ports (e.g. `localhost:8005`).

### host.docker.internal
A hostname Docker Desktop injects so containers can call back to the Windows host.
**Not available in WSL with native Docker** — the Linux daemon never adds it.
Fix: use the service name (`userservice:8000`) to stay inside the Docker network.

### Volume (bind mount)
```
./data  ──►  /app/data   (inside container)
```
A folder on your real disk is "mounted" into the container's filesystem.
Changes in either place are immediately visible to both sides.
Used here so the user database survives container restarts.

### Port Mapping
```
HOST:CONTAINER
8005:8005   → ums-mcp-server   (app.py calls localhost:8005)
8041:8000   → userservice      (exposed but only used if host.docker.internal worked)
6379:6379   → redis-ums        (app.py calls localhost:6379)
6380:5540   → redis-insight    (browser UI)
```
