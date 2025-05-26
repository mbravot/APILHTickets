from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
from sqlalchemy import Table, Column, Integer, String, ForeignKey, Text, DateTime, Date
from sqlalchemy.orm import relationship

db = SQLAlchemy()

CHILE_TZ = pytz.timezone('America/Santiago')  

# 🔹 Modelo Colaborador
class Colaborador(db.Model):
    __tablename__ = 'general_dim_colaborador'
    id = db.Column(Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido_paterno = db.Column(db.String(45), nullable=False)
    apellido_materno = db.Column(db.String(45), nullable=True)
    usuarios = db.relationship('Usuario', backref='colaborador_obj')

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

# 🔹 Modelo Sucursal
class Sucursal(db.Model):
    __tablename__ = 'general_dim_sucursal'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    ubicacion = db.Column(db.String(255), nullable=True)
    id_empresa = db.Column(db.Integer, nullable=True)
    usuarios = db.relationship('Usuario', back_populates='sucursal_obj')

# 🔹 Modelo Rol
class Rol(db.Model):
    __tablename__ = 'ticket_dim_rol'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(45), nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol_obj', lazy='dynamic')

# 🔹 Modelo Usuario
class Usuario(db.Model):
    __tablename__ = 'general_dim_usuario'
    id = db.Column(String(45), primary_key=True)
    id_colaborador = db.Column(Integer, ForeignKey('general_dim_colaborador.id'), nullable=True)
    id_sucursalactiva = db.Column(Integer, ForeignKey('general_dim_sucursal.id'), nullable=False)
    usuario = db.Column(db.String(45), nullable=False)
    clave = db.Column(db.String(255), nullable=False)
    fecha_creacion = db.Column(Date, nullable=False)
    id_estado = db.Column(Integer, ForeignKey('general_dim_estado.id'), nullable=False)
    correo = db.Column(db.String(100), nullable=False)
    id_rol = db.Column(Integer, ForeignKey('ticket_dim_rol.id'), nullable=False)

    # ✅ Relaciones corregidas
    rol_obj = db.relationship('Rol', back_populates='usuarios')
    sucursal_obj = db.relationship('Sucursal', back_populates='usuarios')  
    estado_obj = db.relationship('Estado', back_populates='usuarios')  

    # ✅ Relación con Departamentos (Muchos a Muchos)
    departamentos = relationship("Departamento", secondary=ticket_pivot_departamento_agente, back_populates="agentes")

# 🔹 Modelo TicketEstado
class TicketEstado(db.Model):
    __tablename__ = 'ticket_dim_estado'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

# 🔹 Modelo TicketPrioridad
class TicketPrioridad(db.Model):
    __tablename__ = 'ticket_dim_prioridad'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

# 🔹 Modelo Departamento
class Departamento(db.Model):
    __tablename__ = 'general_dim_departamento'
    id = db.Column(Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    id_empresa = db.Column(Integer, nullable=False, default=1)

    # ✅ Relación con Agentes (Muchos a Muchos)
    agentes = relationship("Usuario", secondary=ticket_pivot_departamento_agente, back_populates="departamentos")

# 🔹 Modelo Ticket
class Ticket(db.Model):
    __tablename__ = 'ticket_fact_registro'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(String(45), ForeignKey('general_dim_usuario.id'), nullable=False)  # Usuario que creó el ticket
    id_agente = db.Column(String(45), ForeignKey('general_dim_usuario.id'), nullable=True)  # Agente asignado al ticket
    id_estado = db.Column(Integer, ForeignKey('ticket_dim_estado.id'), nullable=False)
    id_prioridad = db.Column(Integer, ForeignKey('ticket_dim_prioridad.id'), nullable=False)
    id_departamento = db.Column(Integer, ForeignKey('general_dim_departamento.id'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(Text, nullable=False)
    fecha_creacion = db.Column(DateTime, default=lambda: datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(CHILE_TZ))
    fecha_cierre = db.Column(DateTime, nullable=True)
    adjunto = db.Column(db.String(255), nullable=True) 

    # Relaciones con otros modelos
    usuario = db.relationship('Usuario', foreign_keys=[id_usuario], backref='tickets_creados', lazy='joined')
    agente = db.relationship('Usuario', foreign_keys=[id_agente], backref='tickets_asignados', lazy='joined')  
    estado = db.relationship('TicketEstado', backref='tickets', lazy='joined')
    prioridad = db.relationship('TicketPrioridad', backref='tickets', lazy='joined')
    departamento = db.relationship('Departamento', backref='tickets', lazy='joined')

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

    #fin  
