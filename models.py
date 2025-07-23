from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Text, DateTime, Date
from sqlalchemy.orm import relationship

db = SQLAlchemy()

CHILE_TZ = pytz.timezone('America/Santiago')  

# 🔹 Tabla intermedia para la relación muchos a muchos entre Agentes y Departamentos
ticket_pivot_departamento_agente = Table(
    'ticket_pivot_departamento_agente',
    db.metadata,
    Column('id_usuario', String(45), ForeignKey('general_dim_usuario.id'), primary_key=True),
    Column('id_departamento', Integer, ForeignKey('general_dim_departamento.id'), primary_key=True)
)

# 🔹 Modelo Estado
class Estado(db.Model):
    __tablename__ = 'general_dim_estado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    usuarios = db.relationship('Usuario', back_populates='estado_obj')

# 🔹 Modelo Perfil de Usuario
class PerfilUsuario(db.Model):
    __tablename__ = 'usuario_dim_perfil'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    usuarios = db.relationship('Usuario', backref='perfil_obj')

# 🔹 Modelo Sucursal
class Sucursal(db.Model):
    __tablename__ = 'general_dim_sucursal'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ubicacion = db.Column(db.String(255), nullable=True)
    id_empresa = db.Column(db.Integer, nullable=True)
    usuarios = db.relationship('Usuario', back_populates='sucursal_obj')
    tickets = db.relationship('Ticket', back_populates='sucursal')

# 🔹 Modelo Rol
class Rol(db.Model):
    __tablename__ = 'ticket_dim_rol'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(45), nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol_obj', lazy='dynamic')

# 🔹 Tabla intermedia para la relación muchos a muchos entre Usuarios y Sucursales
usuario_pivot_sucursal_usuario = Table(
    'usuario_pivot_sucursal_usuario',
    db.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('id_sucursal', Integer, ForeignKey('general_dim_sucursal.id'), nullable=False),
    Column('id_usuario', String(45), ForeignKey('general_dim_usuario.id'), nullable=False)
)

# 🔹 Tabla intermedia para la relación muchos a muchos entre Usuarios y Apps
usuario_pivot_app_usuario = Table(
    'usuario_pivot_app_usuario',
    db.metadata,
    Column('id', String(45), primary_key=True, autoincrement=False),
    Column('id_usuario', String(45), ForeignKey('general_dim_usuario.id'), nullable=False),
    Column('id_app', Integer, ForeignKey('general_dim_app.id'), nullable=False)
)

# 🔹 Modelo Usuario
class Usuario(db.Model):
    __tablename__ = 'general_dim_usuario'
    id = db.Column(String(45), primary_key=True)
    id_sucursalactiva = db.Column(Integer, ForeignKey('general_dim_sucursal.id'), nullable=False)
    usuario = db.Column(db.String(45), nullable=False)
    nombre = db.Column(db.String(45), nullable=False)
    apellido_paterno = db.Column(db.String(45), nullable=False)
    apellido_materno = db.Column(db.String(45), nullable=True)
    clave = db.Column(db.String(255), nullable=False)
    fecha_creacion = db.Column(Date, nullable=False)
    id_estado = db.Column(Integer, ForeignKey('general_dim_estado.id'), nullable=False, default=1)
    correo = db.Column(db.String(100), nullable=False)
    id_rol = db.Column(Integer, ForeignKey('ticket_dim_rol.id'), nullable=False, default=3)
    id_perfil = db.Column(Integer, ForeignKey('usuario_dim_perfil.id'), nullable=False, default=1)

    # ✅ Relaciones corregidas
    rol_obj = db.relationship('Rol', back_populates='usuarios')
    sucursal_obj = db.relationship('Sucursal', back_populates='usuarios', foreign_keys=[id_sucursalactiva])
    estado_obj = db.relationship('Estado', back_populates='usuarios')
    
    # ✅ Nueva relación para sucursales autorizadas
    sucursales_autorizadas = relationship("Sucursal", 
                                        secondary=usuario_pivot_sucursal_usuario,
                                        backref=db.backref('usuarios_autorizados', lazy='dynamic'))

    # ✅ Relación con Departamentos (Muchos a Muchos)
    departamentos = relationship("Departamento", secondary=ticket_pivot_departamento_agente, back_populates="agentes")
    
    # ✅ Relación con Apps (Muchos a Muchos)
    apps = relationship("App", secondary=usuario_pivot_app_usuario, back_populates="usuarios")
    
    # ✅ Método para obtener nombre completo
    @property
    def nombre_completo(self):
        apellido_materno = f" {self.apellido_materno}" if self.apellido_materno else ""
        return f"{self.nombre} {self.apellido_paterno}{apellido_materno}".strip()

# 🔹 Modelo TicketEstado
class TicketEstado(db.Model):
    __tablename__ = 'ticket_dim_estado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    
    # Relación con Tickets
    tickets = relationship('Ticket', back_populates='estado')

# 🔹 Modelo TicketPrioridad
class TicketPrioridad(db.Model):
    __tablename__ = 'ticket_dim_prioridad'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

    # Relación con Tickets
    tickets = relationship('Ticket', back_populates='prioridad')

# 🔹 Modelo Categoria
class Categoria(db.Model):
    __tablename__ = 'ticket_dim_categoria'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(String(100), nullable=False)
    id_departamento = db.Column(Integer, ForeignKey('general_dim_departamento.id'), nullable=False)
    
    # Relaciones
    departamento = db.relationship('Departamento', back_populates='categorias')

# 🔹 Modelo Ticket
class Ticket(db.Model):
    __tablename__ = 'ticket_fact_registro'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(String(45), ForeignKey('general_dim_usuario.id'), nullable=False)
    id_agente = db.Column(String(45), ForeignKey('general_dim_usuario.id'), nullable=True)
    id_sucursal = db.Column(Integer, ForeignKey('general_dim_sucursal.id'), nullable=False)
    id_estado = db.Column(Integer, ForeignKey('ticket_dim_estado.id'), nullable=False)
    id_prioridad = db.Column(Integer, ForeignKey('ticket_dim_prioridad.id'), nullable=False)
    id_departamento = db.Column(Integer, ForeignKey('general_dim_departamento.id'), nullable=False)
    id_categoria = db.Column(Integer, ForeignKey('ticket_dim_categoria.id'), nullable=False)
    titulo = db.Column(String(255), nullable=False)
    descripcion = db.Column(Text, nullable=False)
    fecha_creacion = db.Column(DateTime, nullable=False, default=datetime.now)
    fecha_cierre = db.Column(DateTime, nullable=True)
    adjunto = db.Column(String(255), nullable=True)

    # Relaciones
    usuario = db.relationship('Usuario', foreign_keys=[id_usuario], backref='tickets_creados')
    agente = db.relationship('Usuario', foreign_keys=[id_agente], backref='tickets_asignados')
    estado = db.relationship('TicketEstado', back_populates='tickets')
    prioridad = db.relationship('TicketPrioridad', back_populates='tickets')
    departamento = db.relationship('Departamento', back_populates='tickets')
    categoria = db.relationship('Categoria', backref='tickets')
    sucursal = db.relationship('Sucursal', foreign_keys=[id_sucursal], back_populates='tickets')

# 🔹 Modelo TicketComentario
class TicketComentario(db.Model):
    __tablename__ = 'ticket_pivot_comentario_registro'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_ticket = db.Column(db.Integer, ForeignKey('ticket_fact_registro.id', ondelete='CASCADE'), nullable=False)
    id_usuario = db.Column(String(45), ForeignKey('general_dim_usuario.id'), nullable=False)
    comentario = db.Column(Text, nullable=False)
    timestamp = db.Column(DateTime, default=lambda: datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(CHILE_TZ))

    # Relaciones con Ticket y Usuario
    ticket = db.relationship('Ticket', backref=db.backref('comentarios', cascade='all, delete-orphan', passive_deletes=True))
    usuario = db.relationship('Usuario', backref='comentarios', lazy='joined')

# 🔹 Modelo Departamento
class Departamento(db.Model):
    __tablename__ = 'general_dim_departamento'
    id = db.Column(Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    id_empresa = db.Column(Integer, nullable=False, default=1)

    # ✅ Relación con Agentes (Muchos a Muchos)
    agentes = relationship("Usuario", secondary=ticket_pivot_departamento_agente, back_populates="departamentos")
    
    # ✅ Relación con Categorías
    categorias = relationship("Categoria", back_populates="departamento")
    
    # ✅ Relación con Tickets
    tickets = relationship("Ticket", back_populates="departamento")

# 🔹 Modelo App
class App(db.Model):
    __tablename__ = 'general_dim_app'
    id = db.Column(Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(45), nullable=False)
    descripcion = db.Column(db.String(100), nullable=True)
    URL = db.Column(db.String(100), nullable=True)
    
    # Relación con usuarios a través de la tabla pivot
    usuarios = relationship("Usuario", secondary=usuario_pivot_app_usuario, back_populates="apps")
