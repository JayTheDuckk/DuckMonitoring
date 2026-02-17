# Docker Test Hosts

This directory contains Docker configuration to run multiple test hosts for monitoring.

## Quick Start

1. **Make sure your backend is running** on `http://localhost:5001`

2. **Start all test hosts:**
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **View running containers:**
   ```bash
   docker-compose ps
   ```

4. **View logs from all hosts:**
   ```bash
   docker-compose logs -f
   ```

5. **View logs from a specific host:**
   ```bash
   docker-compose logs -f web-server-1
   ```

6. **Stop all hosts:**
   ```bash
   docker-compose down
   ```

## Test Hosts

The following hosts will be created:

- **web-server-1** - Web server instance 1
- **web-server-2** - Web server instance 2
- **db-server** - Database server
- **cache-server** - Cache server
- **app-server-1** - Application server 1
- **app-server-2** - Application server 2

Each host runs the monitoring agent and reports metrics every 30 seconds.

## Configuration

### Change Server URL

If your backend is running on a different host/port, edit `docker-compose.yml` and change:
```yaml
SERVER_URL=http://host.docker.internal:5001
```

For Linux, you may need to use your host IP instead:
```yaml
SERVER_URL=http://192.168.1.100:5001
```

### Change Collection Interval

Edit the `CMD` in `Dockerfile.agent` to change the `--interval` value (in seconds).

### Add More Hosts

Copy one of the service definitions in `docker-compose.yml` and modify the name, hostname, and agent-id.

## Troubleshooting

**Hosts not connecting to backend:**
- Verify backend is running: `curl http://localhost:5001/api/health`
- Check if `host.docker.internal` works on your system (macOS/Windows should work)
- On Linux, you may need to use your actual host IP address

**View agent logs:**
```bash
docker-compose logs web-server-1
```

**Rebuild containers:**
```bash
docker-compose build
docker-compose up -d
```

**Remove all containers and networks:**
```bash
docker-compose down -v
```


