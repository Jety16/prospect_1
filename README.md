
# 📘 README - Deploy de App Fullstack con Cloud SQL Proxy en GCP

## ✅ Objetivo

Desplegar una aplicación fullstack (frontend + backend en Docker) en una **VM de GCP**, utilizando **Cloud SQL como base de datos** y el **Cloud SQL Proxy corriendo directamente en la VM**.

---

## 🧱 Estructura del proyecto

```
project-root/
├── docker-compose.yml
├── nginx/
│   └── default.conf
├── python_backend/
├── frontend/
├── postgres.sql
└── .github/
    └── workflows/
        └── deploy.yml
```

---

## 🧑‍💻 Paso a paso

### 1. 📦 Antes: Base de datos local (dentro de Docker)

El `docker-compose.yml` original incluía un servicio `database` con PostgreSQL 16:

```yaml
services:
  database:
    image: postgres:16
    ...
```

El backend se conectaba a `DB_HOST=prospect_db`.

---

### 2. 🚀 Cambio: Usar Cloud SQL gestionado por GCP

Se eliminó el servicio `database` y ahora el backend se conecta a través de **Cloud SQL Proxy**, ejecutándose directamente en la VM.

---

### 3. 🔐 Instalar Cloud SQL Proxy en la VM

```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.15.2/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/
```

---

### 4. 🔑 Autenticación con GCP

Si la VM usa la cuenta de servicio predeterminada de Compute Engine, no hace falta autenticación manual.

Opcionalmente:

```bash
gcloud auth application-default login
```

---

### 5. 🌐 Levantar el proxy

```bash
nohup cloud-sql-proxy cloud-engineer-test-juanc:us-central1:files \
  --address=0.0.0.0 \
  --port=5432 > cloudsql.log 2>&1 &
```

---

### 6. 🐳 `docker-compose.yml` actualizado

El backend ahora se conecta a través de `DB_HOST=172.17.0.1` (IP del host desde Docker):

```yaml
services:
  backend:
    ...
    environment:
      - DB_HOST=172.17.0.1
      - DB_PORT=5432
      - DB_USER=postgres
      - DB_PASSWORD=postgres
      - DB_NAME=filesdb
```

---

### 7. 🌍 NGINX como reverse proxy

Se agregó un contenedor `nginx` para servir como **punto de entrada único**, exponiendo solo el puerto `80`:

```nginx
server {
    listen 80;

    location / {
        proxy_pass http://frontend:4321;
        ...
    }

    location /api/ {
        rewrite ^/api(/.*)$ $1 break;
        proxy_pass http://backend:5000;
        add_header Access-Control-Allow-Origin *;
        ...
    }

    location /events {
        proxy_pass http://backend:5000/events;
        proxy_buffering off;
        add_header Access-Control-Allow-Origin *;
        ...
    }
}
```

---

### 8. 🌐 Reglas de firewall configuradas

Solo se dejó expuesto:

- ✅ `tcp:80` (HTTP)
- ✅ `tcp:22` (SSH, si es necesario)

Se eliminaron las reglas innecesarias:

```bash
gcloud compute firewall-rules delete allow-frontend-port
gcloud compute firewall-rules delete allow-prospect-frontend
gcloud compute firewall-rules delete allow-prospect-backend
```

---

### 9. 🧠 Configuración del frontend (Astro + Vite)

La app dejó de usar `PUBLIC_API_URL` con IPs duras.  
Ahora, todas las llamadas se hacen **relativas**, aprovechando el proxy de NGINX:

```ts
const API_URL = "/api";
eventSource = new EventSource("/events");
await fetch("/api/upload", { ... });
```

Esto elimina problemas de CORS y simplifica el deployment 💯

---

### 10. 🤖 GitHub Actions para deploy automático

En `.github/workflows/deploy.yml`, se automatiza:

- `ssh` a la VM
- Verificación de Cloud SQL Proxy
- `docker compose up -d --build`

---

## ✅ Conclusión

✅ App fullstack en contenedores  
✅ Base de datos gestionada por Cloud SQL  
✅ Proxy SQL local corriendo en la VM  
✅ Reverse proxy con NGINX (¡sin CORS!)  
✅ Firewall seguro y controlado  
✅ Deploys automáticos con GitHub Actions 🚀

---

## 🧰 Futuras mejoras

- Levantar Cloud SQL Proxy como servicio con `systemd`
- Usar Secret Manager para credenciales sensibles
- Hacer build del frontend y servirlo como estático desde NGINX
- Habilitar HTTPS con Let's Encrypt (Certbot)

---
