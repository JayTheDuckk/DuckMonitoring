# Docker Quickstart Guide

Duck Monitoring can be quickly deployed using Docker Compose. This is the recommended method for most users as it simplifies dependency management and ensures a consistent environment.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running.
- [Docker Compose](https://docs.docker.com/compose/install/) installed.

## Deployment Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/duck-monitoring.git
   cd duck-monitoring
   ```

2. **Start the application:**
   Run the following command in the root of the project where the `docker-compose.yml` file is located:
   ```bash
   docker-compose up -d
   ```
   This will run the process in the background. It will pull the necessary PostgreSQL image and build the `frontend` and `backend` images from the provided Dockerfiles.

3. **Verify the services:**
   You can check the status of your containers to make sure they are running:
   ```bash
   docker-compose ps
   ```
   You should see `db`, `backend`, and `frontend` services with an `Up` status.

4. **Access the Application:**
   - **Frontend (UI):** Open your browser and navigate to `http://localhost:3000` (or the IP address of your server).
   - **Backend API:** The API is accessible at `http://localhost:8000/api/`.

## Initial Setup within the App

Once the application is running, if this is your first time:
1. Navigate to the frontend UI (`http://localhost:3000`).
2. You will be automatically redirected to the `/setup` wizard.
3. Follow the on-screen prompts to create your initial administrator account and register the core server settings.

## Stopping the Application

To gently stop the running containers without deleting your data:
```bash
docker-compose stop
```

To entirely remove the containers, networks, and volumes (Warning: this will delete your PostgreSQL data unless you backed up the named volume!):
```bash
docker-compose down -v
```

## Troubleshooting

If the frontend cannot connect to the backend, ensure that the API base URL in the frontend is correctly pointing to `localhost:8000`. By default, the React app uses standard relative routing which should be proxied by the Nginx configuration inside the frontend container.

To view logs for a specific service (e.g., the backend):
```bash
docker-compose logs -f backend
```
