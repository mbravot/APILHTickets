# 📚 Documentación API - Sistema de Tickets La Hornilla

## 🔗 Información General

- **Base URL**: `https://tickets.lahornilla.cl/api`
- **Versión**: 1.0.0
- **Autenticación**: JWT Bearer Token
- **Formato de respuesta**: JSON

---

## 🔐 **Autenticación y Usuarios**

### **Login de Usuario**
```http
POST /api/login
```

**Descripción:** Autentica un usuario y devuelve tokens JWT.

**Validaciones:**
- ✅ Usuario debe existir y estar activo (`id_estado = 1`)
- ✅ Usuario debe tener acceso a la aplicación (`id_app = 1`)
- ✅ Contraseña debe ser correcta

**Request Body:**
```json
{
    "usuario": "usuario123",
    "clave": "password123"
}
```

**Response (200):**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "usuario": {
        "id": "user123",
        "nombre": "Juan Pérez González",
        "correo": "juan.perez@lahornilla.cl",
        "id_rol": 2,
        "rol": "Agente",
        "sucursal_activa": {
            "id": 1,
            "nombre": "Sucursal Centro"
        },
        "sucursales_autorizadas": [
            {
                "id": 1,
                "nombre": "Sucursal Centro"
            },
            {
                "id": 2,
                "nombre": "Sucursal Norte"
            }
        ]
    }
}
```

**Nota:** El campo `nombre` ahora viene directamente de los campos `nombre`, `apellido_paterno` y `apellido_materno` de la tabla `general_dim_usuario`, no de la tabla de colaboradores.

### Refresh Token
**POST** `/auth/refresh`

Renueva el token de acceso usando el refresh token.

**Headers:**
```
Authorization: Bearer <refresh_token>
```

**Respuesta exitosa (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 🎫 Tickets

### Obtener Tickets
**GET** `/tickets`

Obtiene la lista de tickets según el rol del usuario.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 105,
    "titulo": "Problema con impresora",
    "descripcion": "La impresora no imprime",
    "id_usuario": "44536470-225c-4e3a-8ac4-5dc6d45b5cf2",
    "id_agente": "12345678-1234-1234-1234-123456789012",
    "usuario": "MIGUEL",
    "agente": "Juan Pérez",
    "estado": "Abierto",
    "prioridad": "Baja",
    "departamento": "TI",
    "id_departamento": 1,
    "sucursal": "SANTA VICTORIA",
    "fecha_creacion": "2024-01-15 10:30:00",
    "fecha_cierre": null,
    "adjunto": "archivo.pdf",
    "id_prioridad": 1,
    "id_estado": 1
  }
]
```

### Obtener Ticket Específico
**GET** `/tickets/{id}`

Obtiene los detalles de un ticket específico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "id": 105,
  "titulo": "Problema con impresora",
  "descripcion": "La impresora no imprime",
  "id_usuario": "44536470-225c-4e3a-8ac4-5dc6d45b5cf2",
  "id_agente": "12345678-1234-1234-1234-123456789012",
  "usuario": "MIGUEL",
  "agente": "Juan Pérez",
  "estado": "Abierto",
  "prioridad": "Baja",
  "departamento": "TI",
  "id_departamento": 1,
  "sucursal": "SANTA VICTORIA",
  "fecha_creacion": "2024-01-15 10:30:00",
  "fecha_cierre": null,
  "adjunto": "archivo.pdf",
  "comentarios": [
    {
      "id": 1,
      "id_ticket": 105,
      "id_usuario": "44536470-225c-4e3a-8ac4-5dc6d45b5cf2",
      "usuario": "MIGUEL",
      "comentario": "Ticket creado",
      "creado": "2024-01-15 10:30:00"
    }
  ],
  "id_prioridad": 1,
  "id_estado": 1
}
```

### Crear Ticket
**POST** `/tickets`

Crea un nuevo ticket.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "titulo": "Problema con impresora",
  "descripcion": "La impresora no imprime",
  "id_departamento": 1,
  "id_categoria": 1,
  "id_prioridad": 1,
  "id_estado": 1
}
```

**Respuesta exitosa (201):**
```json
{
  "message": "Ticket creado exitosamente",
  "ticket_id": 105
}
```

### Actualizar Ticket
**PUT** `/tickets/{id}`

Actualiza un ticket existente.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "titulo": "Problema con impresora - Actualizado",
  "descripcion": "La impresora no imprime - Descripción actualizada",
  "id_prioridad": 2,
  "id_estado": 2
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Ticket actualizado correctamente"
}
```

### Eliminar Ticket
**DELETE** `/tickets/{id}`

Elimina un ticket.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "message": "Ticket eliminado correctamente"
}
```

### Cerrar Ticket
**PUT** `/tickets/{id}/cerrar`

Cierra un ticket.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "message": "Ticket cerrado correctamente"
}
```

---

## 💬 Comentarios

### Obtener Comentarios de Ticket
**GET** `/tickets/{ticket_id}/comentarios`

Obtiene los comentarios de un ticket específico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "id_ticket": 105,
    "id_usuario": "44536470-225c-4e3a-8ac4-5dc6d45b5cf2",
    "usuario": "MIGUEL",
    "comentario": "Ticket creado",
    "creado": "2024-01-15 10:30:00"
  }
]
```

### Agregar Comentario
**POST** `/tickets/{ticket_id}/comentarios`

Agrega un comentario a un ticket.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "comentario": "Nuevo comentario sobre el ticket"
}
```

**Respuesta exitosa (201):**
```json
{
  "message": "Comentario agregado correctamente"
}
```

---

## 👥 Usuarios

### **Obtener Usuarios**
```http
GET /api/usuarios
```

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
[
    {
        "id": "user123",
        "nombre": "Juan Pérez González",
        "correo": "juan.perez@lahornilla.cl",
        "rol": "Agente",
        "sucursal_activa": {
            "id": 1,
            "nombre": "Sucursal Centro"
        },
        "sucursales_autorizadas": [
            {
                "id": 1,
                "nombre": "Sucursal Centro"
            }
        ],
        "estado": "Activo",
        "id_departamento": [1, 2]
    }
]
```

### **Registrar Usuario**
```http
POST /api/usuarios
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "usuario": "nuevo_usuario",
    "nombre": "Juan",
    "apellido_paterno": "Pérez",
    "apellido_materno": "González",
    "correo": "juan.perez@lahornilla.cl",
    "clave": "password123",
    "id_rol": 2,
    "id_sucursalactiva": 1,
    "id_estado": 1,
    "id_perfil": 1
}
```

**Response (201):**
```json
{
    "message": "Usuario registrado exitosamente",
    "usuario": {
        "id": "user123",
        "nombre": "Juan Pérez González",
        "correo": "juan.perez@lahornilla.cl",
        "rol": "Agente"
    }
}
```

**Nota:** Los campos `nombre`, `apellido_paterno` y `apellido_materno` ahora se almacenan directamente en la tabla `general_dim_usuario`.

### **Actualizar Usuario**
```http
PUT /api/usuarios/<id>
```

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
    "nombre": "Juan Carlos",
    "apellido_paterno": "Pérez",
    "apellido_materno": "González",
    "correo": "juan.perez@lahornilla.cl",
    "id_rol": 2,
    "id_sucursalactiva": 1,
    "id_estado": 1,
    "id_perfil": 1
}
```

**Response (200):**
```json
{
    "message": "Usuario actualizado correctamente",
    "usuario": {
        "id": "user123",
        "nombre": "Juan Carlos Pérez González",
        "correo": "juan.perez@lahornilla.cl",
        "rol": "Agente",
        "sucursal_activa": {
            "id": 1,
            "nombre": "Sucursal Centro"
        },
        "sucursales_autorizadas": [
            {
                "id": 1,
                "nombre": "Sucursal Centro"
            }
        ],
        "estado": "Activo"
    }
}
```

### Eliminar Usuario
**DELETE** `/usuarios/{user_id}`

Elimina un usuario (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "message": "Usuario eliminado correctamente"
}
```

### Cambiar Clave
**PUT** `/usuarios/{user_id}/cambiar-clave`

Cambia la contraseña de un usuario.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "clave_actual": "clave_actual",
  "clave_nueva": "nueva_clave"
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Clave cambiada correctamente"
}
```

---

## 🏢 Departamentos

### Obtener Departamentos
**GET** `/departamentos`

Obtiene la lista de departamentos.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "TI"
  },
  {
    "id": 2,
    "nombre": "RRHH"
  }
]
```

### Crear Departamento
**POST** `/departamentos`

Crea un nuevo departamento (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "nombre": "Nuevo Departamento"
}
```

**Respuesta exitosa (201):**
```json
{
  "message": "Departamento creado exitosamente",
  "id": 3
}
```

### Editar Departamento
**PUT** `/departamentos/{id}`

Edita un departamento existente (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "nombre": "Departamento Actualizado"
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Departamento actualizado correctamente"
}
```

### Eliminar Departamento
**DELETE** `/departamentos/{id}`

Elimina un departamento (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "message": "Departamento eliminado correctamente"
}
```

---

## 🏪 Sucursales

### Obtener Sucursales
**GET** `/sucursales`

Obtiene la lista de sucursales.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 103,
    "nombre": "SANTA VICTORIA"
  },
  {
    "id": 104,
    "nombre": "CULLIPEUMO"
  }
]
```

---

## 📊 Estados y Prioridades

### Obtener Estados
**GET** `/estados`

Obtiene la lista de estados de tickets.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "Abierto"
  },
  {
    "id": 2,
    "nombre": "En Proceso"
  },
  {
    "id": 3,
    "nombre": "Cerrado"
  }
]
```

### Obtener Prioridades
**GET** `/prioridades`

Obtiene la lista de prioridades de tickets.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "Baja"
  },
  {
    "id": 2,
    "nombre": "Media"
  },
  {
    "id": 3,
    "nombre": "Alta"
  },
  {
    "id": 4,
    "nombre": "Crítica"
  }
]
```

---

## 🎯 Agentes

### Obtener Agentes
**GET** `/agentes`

Obtiene la lista de agentes (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": "12345678-1234-1234-1234-123456789012",
    "nombre": "Juan Pérez"
  },
  {
    "id": "87654321-4321-4321-4321-210987654321",
    "nombre": "María García"
  }
]
```

### Asignar Ticket
**PUT** `/tickets/{ticket_id}/asignar`

Asigna un agente a un ticket.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "id_agente": "12345678-1234-1234-1234-123456789012"
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Ticket reasignado correctamente"
}
```

### Obtener Agentes por Departamento
**GET** `/departamentos/{id_departamento}/agentes`

Obtiene los agentes de un departamento específico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": "12345678-1234-1234-1234-123456789012",
    "nombre": "Juan Pérez"
  }
]
```

---

## 📱 Aplicaciones (Apps)

### Obtener Apps Disponibles
**GET** `/apps`

Obtiene la lista de todas las apps disponibles.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "Sistema de Tickets",
    "descripcion": "Sistema para gestión de tickets de soporte",
    "url": "https://tickets.lahornilla.cl"
  }
]
```

### Obtener Apps del Usuario
**GET** `/usuario/apps`

Obtiene las apps a las que tiene acceso el usuario actual.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "Sistema de Tickets",
    "descripcion": "Sistema para gestión de tickets de soporte",
    "url": "https://tickets.lahornilla.cl"
  }
]
```

---

## 🔧 Administración de Apps (Solo Administradores)

### Obtener Todas las Apps
**GET** `/admin/apps`

Obtiene todas las apps con información completa.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "Sistema de Tickets",
    "descripcion": "Sistema para gestión de tickets de soporte",
    "url": "https://tickets.lahornilla.cl"
  }
]
```

### Crear App
**POST** `/admin/apps`

Crea una nueva aplicación.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "nombre": "Nueva App",
  "descripcion": "Descripción de la nueva app",
  "url": "https://nueva-app.lahornilla.cl"
}
```

**Respuesta exitosa (201):**
```json
{
  "message": "App creada exitosamente",
  "app": {
    "id": 2,
    "nombre": "Nueva App",
    "descripcion": "Descripción de la nueva app",
    "url": "https://nueva-app.lahornilla.cl"
  }
}
```

### Editar App
**PUT** `/admin/apps/{app_id}`

Edita una aplicación existente.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "nombre": "App Actualizada",
  "descripcion": "Descripción actualizada",
  "url": "https://app-actualizada.lahornilla.cl"
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "App actualizada correctamente",
  "app": {
    "id": 1,
    "nombre": "App Actualizada",
    "descripcion": "Descripción actualizada",
    "url": "https://app-actualizada.lahornilla.cl"
  }
}
```

### Eliminar App
**DELETE** `/admin/apps/{app_id}`

Elimina una aplicación.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "message": "App eliminada correctamente"
}
```

### Obtener Usuarios con Apps
**GET** `/admin/usuarios-apps`

Obtiene todos los usuarios con sus apps asignadas (ordenados alfabéticamente).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": "44536470-225c-4e3a-8ac4-5dc6d45b5cf2",
    "nombre": "MIGUEL",
    "correo": "mbravo@lahornilla.cl",
    "rol": "AGENTE",
    "estado": "Activo",
    "apps": [
      {
        "id": 1,
        "nombre": "Sistema de Tickets",
        "descripcion": "Sistema para gestión de tickets de soporte",
        "url": "https://tickets.lahornilla.cl"
      }
    ]
  }
]
```

### Obtener Apps de Usuario Específico
**GET** `/admin/usuarios/{user_id}/apps`

Obtiene las apps asignadas a un usuario específico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "usuario": {
    "id": "44536470-225c-4e3a-8ac4-5dc6d45b5cf2",
    "nombre": "MIGUEL",
    "correo": "mbravo@lahornilla.cl",
    "rol": "AGENTE"
  },
  "apps": [
    {
      "id": 1,
      "nombre": "Sistema de Tickets",
      "descripcion": "Sistema para gestión de tickets de soporte",
      "url": "https://tickets.lahornilla.cl"
    }
  ]
}
```

### Asignar Apps a Usuario
**PUT** `/admin/usuarios/{user_id}/apps`

Asigna apps a un usuario específico.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "app_ids": [1, 2, 3]
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Apps asignadas correctamente",
  "usuario": {
    "id": "44536470-225c-4e3a-8ac4-5dc6d45b5cf2",
    "nombre": "MIGUEL",
    "correo": "mbravo@lahornilla.cl",
    "apps": [
      {
        "id": 1,
        "nombre": "Sistema de Tickets",
        "descripcion": "Sistema para gestión de tickets de soporte",
        "url": "https://tickets.lahornilla.cl"
      }
    ]
  }
}
```

---

## 📁 Archivos

### Subir Archivo
**POST** `/tickets/{id}/upload`

Sube un archivo adjunto a un ticket.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Body:**
```
file: [archivo]
```

**Respuesta exitosa (200):**
```json
{
  "message": "Archivo subido correctamente",
  "adjunto": "t105_abc123.pdf"
}
```

### Eliminar Archivo
**DELETE** `/tickets/{id}/adjunto/{nombre_adjunto}`

Elimina un archivo adjunto de un ticket.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
{
  "message": "Archivo eliminado correctamente"
}
```

### Descargar Archivo
**GET** `/uploads/{filename}`

Descarga un archivo adjunto.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta:** Archivo binario

---

## 🔄 Estados de Ticket

### Cambiar Estado de Ticket
**PUT** `/tickets/{ticket_id}/estado`

Cambia el estado de un ticket.

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "id_estado": 2
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Estado del ticket actualizado correctamente"
}
```

---

## 📋 Categorías

### Obtener Categorías por Departamento
**GET** `/categorias?departamento_id={id}`

Obtiene las categorías de un departamento específico.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "Hardware"
  },
  {
    "id": 2,
    "nombre": "Software"
  }
]
```

---

## 🏢 Gestión de Agentes

### Obtener Agentes Agrupados por Sucursal
**GET** `/agentes/agrupados-por-sucursal`

Obtiene los agentes agrupados por sucursal (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "sucursal": "SANTA VICTORIA",
    "agentes": [
      {
        "id": "12345678-1234-1234-1234-123456789012",
        "nombre": "Juan Pérez",
        "correo": "juan@lahornilla.cl"
      }
    ]
  }
]
```

### Obtener Agentes y Departamentos
**GET** `/agentes/departamentos`

Obtiene los agentes con sus departamentos asignados (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": "12345678-1234-1234-1234-123456789012",
    "nombre": "Juan Pérez",
    "departamentos": [
      {
        "id": 1,
        "nombre": "TI"
      }
    ]
  }
]
```

### Asignar Departamentos a Agente
**PUT** `/agentes/{id_agente}/departamentos`

Asigna departamentos a un agente (solo administradores).

**Headers:**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Body:**
```json
{
  "departamentos": [1, 2, 3]
}
```

**Respuesta exitosa (200):**
```json
{
  "message": "Departamentos asignados correctamente"
}
```

---

## 🔐 Roles

### Obtener Roles
**GET** `/roles`

Obtiene la lista de roles disponibles.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```json
[
  {
    "id": 1,
    "nombre": "ADMINISTRADOR"
  },
  {
    "id": 2,
    "nombre": "AGENTE"
  },
  {
    "id": 3,
    "nombre": "USUARIO"
  }
]
```

---

## 📊 Estados de Usuarios

### Obtener Estados de Usuarios
**GET** `/usuarios/estados`

Obtiene la lista de estados de usuarios.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Respuesta exitosa (200):**
```
```