from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import ipaddress
from sqlalchemy.orm import validates
from sqlalchemy import event, inspect, UniqueConstraint, Index



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
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)
    status = Column(String(50), default='active')
    
    # Relationships
    services = relationship('Service', back_populates='owner')
    owned_ips = relationship('OwnerIP', back_populates='owner', cascade="all, delete-orphan")
    owned_domains = relationship('OwnerDomain', back_populates='owner', cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_owner_status', 'status'),
        Index('idx_owner_name', 'name'),
    )

# New models to track owner IPs and domains
class OwnerIP(Base):
    __tablename__ = 'owner_ips'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('owners.id'), nullable=False)
    ip = Column(String(45), nullable=False)  # Support both IPv4 and IPv6
    added_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship('Owner', back_populates='owned_ips')
    
    __table_args__ = (
        UniqueConstraint('ip', name='uix_owner_ip'),
        Index('idx_owner_ip', 'ip'),
    )

class OwnerDomain(Base):
    __tablename__ = 'owner_domains'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('owners.id'), nullable=False)
    domain = Column(String(255), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship('Owner', back_populates='owned_domains')
    
    __table_args__ = (
        UniqueConstraint('domain', name='uix_owner_domain'),
        Index('idx_owner_domain', 'domain'),
    )

class Service(Base):
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True)
    ip = Column(String(45), nullable=False)
    port = Column(Integer, nullable=False)
    asn = Column(String(50))
    country = Column(String(100))
    domain = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    banner_data = Column(Text)
    http_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    fruit_id = Column(Integer, ForeignKey('fruits.id'), nullable=True)
    fruit_type_id = Column(Integer, ForeignKey('fruit_types.id'), nullable=True)
    owner_id = Column(Integer, ForeignKey('owners.id'), nullable=True)
    
    fruit = relationship('Fruit', back_populates='services')
    fruit_type = relationship('FruitType', back_populates='services')
    owner = relationship('Owner', back_populates='services')

    @validates('fruit')
    def validate_fruit(self, key, fruit):
        """Auto-update fruit_type_id when fruit is set"""
        if fruit is not None:
            self.fruit_type_id = fruit.fruit_type_id
            return fruit
        return None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'fruit' in kwargs and kwargs['fruit'] is not None:
            self.fruit_type_id = kwargs['fruit'].fruit_type_id

    @validates('ip', 'domain')
    def validate_ownership_fields(self, key, value):
        """Auto-update owner based on IP or domain match"""
        if value:
            session = inspect(self).session
            if session:
                if key == 'ip':
                    owner_ip = session.query(OwnerIP).filter_by(ip=value).first()
                    if owner_ip:
                        self.owner_id = owner_ip.owner_id
                elif key == 'domain':
                    owner_domain = session.query(OwnerDomain).filter_by(domain=value).first()
                    if owner_domain:
                        self.owner_id = owner_domain.owner_id
        return value




class FruitType(Base):
    __tablename__ = 'fruit_types'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    
    fruits = relationship('Fruit', back_populates='fruit_type')
    services = relationship('Service', back_populates='fruit_type')  # Add this
    recipes = relationship('Recipe', secondary=fruit_type_recipe, back_populates='fruit_types')

class Fruit(Base):
    __tablename__ = 'fruits'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    country_of_origin = Column(String(100))
    date_picked = Column(DateTime)
    fruit_type_id = Column(Integer, ForeignKey('fruit_types.id'), nullable=False)
    
    fruit_type = relationship('FruitType', back_populates='fruits')
    services = relationship('Service', back_populates='fruit')

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


# Event listeners for Service model
@event.listens_for(Service, 'before_insert')
def set_owner_from_ip_domain(mapper, connection, target):
    """Set owner_id based on IP or domain before insert if not already set"""
    if target.owner_id is None:
        session = inspect(target).session
        if session:
            # Check IP first
            if target.ip:
                owner_ip = session.query(OwnerIP).filter_by(ip=target.ip).first()
                if owner_ip:
                    target.owner_id = owner_ip.owner_id
                    return
            
            # Check domain if no IP match
            if target.domain:
                owner_domain = session.query(OwnerDomain).filter_by(domain=target.domain).first()
                if owner_domain:
                    target.owner_id = owner_domain.owner_id

@event.listens_for(Service, 'before_update')
def update_owner_from_ip_domain(mapper, connection, target):
    """Update owner_id when IP or domain changes"""
    ip_changed = inspect(target).attrs.ip.history.has_changes()
    domain_changed = inspect(target).attrs.domain.history.has_changes()
    
    if ip_changed or domain_changed:
        session = inspect(target).session
        if session:
            # Check IP first if it changed
            if ip_changed and target.ip:
                owner_ip = session.query(OwnerIP).filter_by(ip=target.ip).first()
                if owner_ip:
                    target.owner_id = owner_ip.owner_id
                    return
            
            # Check domain if it changed and no IP match
            if domain_changed and target.domain:
                owner_domain = session.query(OwnerDomain).filter_by(domain=target.domain).first()
                if owner_domain:
                    target.owner_id = owner_domain.owner_id

# Event listeners for OwnerIP model
@event.listens_for(OwnerIP, 'after_insert')
def update_services_for_new_ip(mapper, connection, target):
    """Update existing services that match the new IP"""
    session = inspect(target).session
    if session:
        services = session.query(Service).filter_by(ip=target.ip, owner_id=None).all()
        for service in services:
            service.owner_id = target.owner_id

# Event listeners for OwnerDomain model
@event.listens_for(OwnerDomain, 'after_insert')
def update_services_for_new_domain(mapper, connection, target):
    """Update existing services that match the new domain"""
    session = inspect(target).session
    if session:
        services = session.query(Service).filter_by(domain=target.domain, owner_id=None).all()
        for service in services:
            service.owner_id = target.owner_id

# Event listeners
@event.listens_for(Fruit, 'after_update')
def update_service_fruit_types(mapper, connection, target):
    """Update all related services when a fruit's type changes"""
    if inspect(target).attrs.fruit_type_id.history.has_changes():
        # Using the Session associated with the target
        session = inspect(target).session
        if session:
            # Update all related services
            for service in target.services:
                service.fruit_type_id = target.fruit_type_id
            # No need to commit here as it's part of the ongoing transaction
