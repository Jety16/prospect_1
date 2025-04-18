# 📘 README - Deploy de App Fullstack con Cloud SQL Proxy en GCP

## ✅ Objetivo

Desplegar una aplicación fullstack (frontend + backend en Docker) en una **VM de GCP**, utilizando **Cloud SQL como base de datos** y el **Cloud SQL Proxy corriendo directamente en la VM**.

---

## 🧱 Estructura del proyecto

```
project-root/
├── docker-compose.yml
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

El `docker-compose.yml` original incluía un servicio `database` con PostgreSQL 16, así:

```yaml
services:
  database:
    image: postgres:16
    ...
```

El backend se conectaba a `DB_HOST=prospect_db`, y se usaban volúmenes para persistencia y scripts de inicialización.

---

### 2. 🚀 Cambio: Usar Cloud SQL gestionado por GCP

La base de datos se movió a **Cloud SQL (PostgreSQL)**.  
Se eliminó el servicio `database` del `docker-compose.yml`, y ahora el backend se conecta a través del **Cloud SQL Proxy** que se ejecuta en la VM.

---

### 3. 🔐 Instalar Cloud SQL Proxy en la VM

```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.15.2/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/
```

---

### 4. 🔑 Autenticación con GCP (una sola vez)
a
Si estás usando una VM con permisos predeterminados (como Compute Engine default service account), no necesitás `credentials.json`.

Pero, por si acaso, se autenticó:

```bash
gcloud auth application-default login
```

---

### 5. 🌐 Levantar Cloud SQL Proxy en la VM

```bash
nohup cloud-sql-proxy cloud-engineer-test-juanc:us-central1:files \
  --address=0.0.0.0 \
  --port=5432 > cloudsql.log 2>&1 &
```

Este comando:

- Abre el puerto `5432` a conexiones externas (como Docker o tu PC local)
- Se ejecuta en segundo plano con logs en `cloudsql.log`

---

### 6. 🐳 Actualización del `docker-compose.yml`

Se quitó el servicio `database` y el backend ahora se conecta a la IP de la VM desde Docker:

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

### 7. 🤖 GitHub Actions para deploy automático

El workflow `deploy.yml`:

- Se ejecuta al hacer `push` a `produccion`
- Se conecta a la VM por SSH
- Verifica si el proxy está corriendo (si no, lo arranca)
- Hace `docker compose up -d --build`

---

## ✅ Conclusión

✅ App fullstack corriendo en Docker  
✅ Base de datos totalmente gestionada en Cloud SQL  
✅ Proxy corriendo en la VM  
✅ Deploy automatizado con GitHub Actions

---

## 🧰 Futuras mejoras (opcional)

- Hacer que el proxy se levante automáticamente con la VM (como servicio `systemd`)
- Usar DNS internos de GCP para mayor resiliencia (`*.c.<PROJECT>.internal`)
- Habilitar Secret Manager para variables sensibles
