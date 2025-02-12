from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import ipaddress

Base = declarative_base()

# Association tables
fruit_type_recipe = Table(
    'fruit_type_recipe',
    Base.metadata,
    Column('fruit_type_id', Integer, ForeignKey('fruit_types.id')),
    Column('recipe_id', Integer, ForeignKey('recipes.id'))
)

group_member = Table(
    'group_member',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('group_id', Integer, ForeignKey('groups.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    groups = relationship('Group', secondary=group_member, back_populates='members')
    saved_filters = relationship('SavedFilter', back_populates='user')

class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    members = relationship('User', secondary=group_member, back_populates='groups')
    shared_filters = relationship('SavedFilter', back_populates='group')

class Owner(Base):
    __tablename__ = 'owners'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    contact_info = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to services
    services = relationship('Service', back_populates='owner')

class Service(Base):
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True)
    ip = Column(String(45), nullable=False)  # Support both IPv4 and IPv6
    port = Column(Integer, nullable=False)
    asn = Column(String(50))
    country = Column(String(100))
    domain = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    banner_data = Column(Text)
    http_data = Column(JSON)  # Store HTTP response data as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    fruit_id = Column(Integer, ForeignKey('fruits.id'))
    owner_id = Column(Integer, ForeignKey('owners.id'))
    
    # Relationships
    fruit = relationship('Fruit', back_populates='services')
    owner = relationship('Owner', back_populates='services')

class FruitType(Base):
    __tablename__ = 'fruit_types'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    
    fruits = relationship('Fruit', back_populates='fruit_type')
    recipes = relationship('Recipe', secondary=fruit_type_recipe, back_populates='fruit_types')

class Fruit(Base):
    __tablename__ = 'fruits'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    country_of_origin = Column(String(100))
    date_picked = Column(DateTime)
    fruit_type_id = Column(Integer, ForeignKey('fruit_types.id'), nullable=False)
    
    fruit_type = relationship('FruitType', back_populates='fruits')
    services = relationship('Service', back_populates='fruit')  # New relationship

class Recipe(Base):
    __tablename__ = 'recipes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    instructions = Column(Text)
    preparation_time = Column(Integer)  # in minutes
    created_at = Column(DateTime, default=datetime.utcnow)
    
    fruit_types = relationship('FruitType', secondary=fruit_type_recipe, back_populates='recipes')

class SavedFilter(Base):
    __tablename__ = 'saved_filters'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(200))
    filter_criteria = Column(Text, nullable=False)  # Stored as JSON
    visible_columns = Column(Text, nullable=False)  # Stored as JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id'))
    
    user = relationship('User', back_populates='saved_filters')
    group = relationship('Group', back_populates='shared_filters')