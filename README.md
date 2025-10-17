# ⚙️ Neogend-FRP-API

The official **backend API** for the [Neogend-FRP](https://neogend-frp.fr) project.
Built with **FastAPI**, it manages authentication, access control, and data operations related to the RP files and users within the Neogend-FRP ecosystem.

---

## 🚀 Overview

**Neogend-FRP-API** serves as the backbone of the Neogend-FRP application.
It handles all the core logic related to:

* User authentication and authorization
* Role and permission verification
* RP file management and access
* Secure data persistence

> This API is **private** — it only responds to **authenticated and validated accounts**.
> Unauthorized or unverified users cannot access any endpoint.

---

## 🧠 Tech Stack

* **Framework:** FastAPI
* **Language:** Python
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Validation:** Pydantic
* **Authentication:** JWT (Access & Refresh tokens)
* **Containerization:** Docker Compose
* **Frontend:** [Neogend-FRP](https://neogend-frp.fr) (React, Vite, Tailwind)

---

## 🔐 Security & Access Control

Authentication is fully token-based using **JWTs**:

* **Access tokens** for short-term authorization
* **Refresh tokens** for renewing sessions securely

Each API call verifies user permissions according to their **role**:

| Role              | Permissions                                     |
| ----------------- | ----------------------------------------------- |
| **Owner**         | Full access to all routes and configuration     |
| **Administrator** | Can manage users and validate new accounts      |
| **Moderator**     | Limited write permissions                       |
| **User**          | Restricted access; may only read/write own data |

> The API enforces role-based access on every protected route.

---

## 🌐 Deployment

The API is designed for production deployment using **Docker Compose**, alongside the frontend and PostgreSQL database.

**Production URL:** [https://neogend-frp.fr](https://neogend-frp.fr/api)
**API Documentation:** [https://neogend-frp.fr/api/docs](https://neogend-frp.fr/api/docs)

---

## ⚙️ Environment & Configuration

The API requires environment variables for database connection, JWT secrets, and other internal settings.

> These must **never be shared or exposed publicly**.

Example (values omitted for security):

```bash
DATABASE_URL=...
JWT_SECRET=...
JWT_REFRESH_SECRET=...
```

---

## 🔧 Internal Logic

* Authentication & token management handled via FastAPI dependencies
* Database interaction through SQLAlchemy models
* Data validation using Pydantic schemas
* Centralized exception handling for clean API responses

---

## 🧱 Integration with Frontend

The Neogend-FRP frontend communicates directly with this API for:

* Account login and validation
* Access to RP files and document creation
* Data synchronization and permission control

Both services are **interconnected** within the same Docker Compose network for internal communication.

---

## 🪪 Version & License

**Version:** 1.0 (Initial Release)

### License

This project and its content are the exclusive property of **Maxime Czegledi**.
**Any use, modification, redistribution, or reproduction** — in part or in full — is **strictly prohibited without prior written authorization** from the author.

© 2025 **Maxime Czegledi**
All rights reserved.

---

## 🤝 Contributing

Contributions are welcome!
You can submit:

* **Pull Requests** for code improvements
* **Issues** for bug reports or enhancement ideas

---

## 🧾 Changelog

**v1.0 – Initial Release**

* FastAPI setup with PostgreSQL and SQLAlchemy
* JWT authentication (Access + Refresh tokens)
* Role-based authorization
* Connection with Neogend-FRP frontend
* Docker Compose integration

---

## 🧷 Badges (example)

![Version](https://img.shields.io/badge/version-1.0-blue.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-Restricted-red.svg)

---

## 🧩 Notes

This API is **private** and exclusively intended for the **Neogend-FRP project**.
It is **not open for public use** or redistribution without explicit authorization.
