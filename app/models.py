from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Table, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import ipaddress
from sqlalchemy.orm import validates
from sqlalchemy import event, inspect, UniqueConstraint, Index
from sqlalchemy import and_, or_




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

    #TODO this is where I should do Ownership by /24s and by domain+subdomain things. Obviously
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
    date_picked = Column(DateTime)
    fruit_type_id = Column(Integer, ForeignKey('fruit_types.id'), nullable=False)
    match_type = Column(String(50))  # banner, domain, etc.
    match_regex = Column(String(500))  # The regex pattern to match
    
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

@event.listens_for(Fruit, 'after_insert')
def match_services_on_create(mapper, connection, target):
    """Match and update services when a new fruit is created"""
    if target.match_type and target.match_regex:
        try:
            session = inspect(target).session
            if session:
                import re
                pattern = re.compile(target.match_regex)
                
                if target.match_type == 'banner':
                    matching_services = session.query(Service).filter(
                        and_(
                            Service.banner_data.isnot(None),
                            Service.fruit_id.is_(None)
                        )
                    ).all()
                    for service in matching_services:
                        if service.banner_data and pattern.search(service.banner_data):
                            service.fruit_id = target.id
                            service.fruit_type_id = target.fruit_type_id
                
                elif target.match_type == 'domain':
                    matching_services = session.query(Service).filter(
                        and_(
                            Service.domain.isnot(None),
                            Service.fruit_id.is_(None)
                        )
                    ).all()
                    for service in matching_services:
                        if service.domain and pattern.search(service.domain):
                            service.fruit_id = target.id
                            service.fruit_type_id = target.fruit_type_id
                
        except re.error:
            # Log error but don't interrupt the transaction
            print(f"Invalid regex pattern for fruit {target.name}: {target.match_regex}")

@event.listens_for(Fruit, 'after_update')
def update_service_matches(mapper, connection, target):
    """Update service matches when fruit matching criteria changes"""
    session = inspect(target).session
    if not session:
        return

    # Check what changed
    inspect_target = inspect(target)
    match_type_changed = inspect_target.attrs.match_type.history.has_changes()
    match_regex_changed = inspect_target.attrs.match_regex.history.has_changes()
    fruit_type_changed = inspect_target.attrs.fruit_type_id.history.has_changes()

    # If matching criteria changed, re-evaluate all services
    if match_type_changed or match_regex_changed:
        try:
            # Clear existing matches
            session.query(Service).filter(Service.fruit_id == target.id).update(
                {"fruit_id": None, "fruit_type_id": None}
            )

            if target.match_type and target.match_regex:
                import re
                pattern = re.compile(target.match_regex)
                
                if target.match_type == 'banner':
                    matching_services = session.query(Service).filter(
                        Service.banner_data.isnot(None)
                    ).all()
                    for service in matching_services:
                        if service.banner_data and pattern.search(service.banner_data):
                            service.fruit_id = target.id
                            service.fruit_type_id = target.fruit_type_id
                
                elif target.match_type == 'domain':
                    matching_services = session.query(Service).filter(
                        Service.domain.isnot(None)
                    ).all()
                    for service in matching_services:
                        if service.domain and pattern.search(service.domain):
                            service.fruit_id = target.id
                            service.fruit_type_id = target.fruit_type_id
                
        except re.error:
            print(f"Invalid regex pattern for fruit {target.name}: {target.match_regex}")
    
    # If only fruit_type changed, update existing services
    elif fruit_type_changed:
        for service in target.services:
            service.fruit_type_id = target.fruit_type_id

@event.listens_for(Service, 'after_update')
def check_service_matches(mapper, connection, target):
    """Check if service matches any fruits when its data changes"""
    session = inspect(target).session
    if not session:
        return

    inspect_target = inspect(target)
    banner_changed = inspect_target.attrs.banner_data.history.has_changes()
    domain_changed = inspect_target.attrs.domain.history.has_changes()

    if not (banner_changed or domain_changed):
        return

    # Clear existing fruit association if any
    target.fruit_id = None
    target.fruit_type_id = None

    # Check all fruits for matches
    fruits = session.query(Fruit).filter(
        and_(
            Fruit.match_type.isnot(None),
            Fruit.match_regex.isnot(None)
        )
    ).all()

    for fruit in fruits:
        try:
            import re
            pattern = re.compile(fruit.match_regex)
            
            if fruit.match_type == 'banner' and target.banner_data:
                if pattern.search(target.banner_data):
                    target.fruit_id = fruit.id
                    target.fruit_type_id = fruit.fruit_type_id
                    break
            
            elif fruit.match_type == 'domain' and target.domain:
                if pattern.search(target.domain):
                    target.fruit_id = fruit.id
                    target.fruit_type_id = fruit.fruit_type_id
                    break
                    
        except re.error:
            print(f"Invalid regex pattern for fruit {fruit.name}: {fruit.match_regex}")
            continue
