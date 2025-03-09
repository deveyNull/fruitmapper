#!/usr/bin/env python3
"""
Enhanced database initialization script for the Fruit Platform.
This script loads the updated sample data and demonstrates the ownership matching
and service fingerprinting functionality.
"""

import os
import csv
import json
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models
from models import Base, User, FruitType, Fruit, Recipe, Owner, OwnerIP, OwnerDomain, Service
from passlib.hash import bcrypt

SAMPLE_DATA_DIR = ""

# Create database engine
DATABASE_URL = "sqlite:///./fruit_platform.db"
engine = create_engine(DATABASE_URL)

# Create all tables
Base.metadata.create_all(engine)

# Create session
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def load_fruit_types(filename):
    """Load fruit types from CSV file."""
    filepath = os.path.join(SAMPLE_DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found")
        return
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            existing = session.query(FruitType).filter_by(name=row['name']).first()
            if existing:
                # Update existing fruit type
                existing.description = row['description']
                count += 1
            else:
                # Create new fruit type
                fruit_type = FruitType(
                    name=row['name'],
                    description=row['description']
                )
                session.add(fruit_type)
                count += 1
    
    session.commit()
    print(f"Loaded {count} fruit types from {filename}")

def load_fruits(filename):
    """Load fruits from CSV file."""
    filepath = os.path.join(SAMPLE_DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found")
        return
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            # Get fruit type
            fruit_type = session.query(FruitType).filter_by(name=row['fruit_type']).first()
            if not fruit_type:
                print(f"Warning: Fruit type {row['fruit_type']} not found")
                continue
            
            existing = session.query(Fruit).filter_by(name=row['name']).first()
            if existing:
                # Update existing fruit
                existing.match_type = row['match_type']
                existing.match_regex = row['match_regex']
                existing.date_picked = datetime.strptime(row['date_picked'], '%Y-%m-%d')
                existing.fruit_type_id = fruit_type.id
                count += 1
            else:
                # Create new fruit
                fruit = Fruit(
                    name=row['name'],
                    date_picked=datetime.strptime(row['date_picked'], '%Y-%m-%d'),
                    fruit_type_id=fruit_type.id,
                    match_type=row['match_type'],
                    match_regex=row['match_regex']
                )
                session.add(fruit)
                count += 1
    
    session.commit()
    print(f"Loaded {count} fruits from {filename}")

def load_owners(filename):
    """Load owners and their IP/domain ownership records from CSV file."""
    filepath = os.path.join(SAMPLE_DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found")
        return
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        owner_count = 0
        ip_count = 0
        domain_count = 0
        
        for row in reader:
            # Create or update owner
            existing = session.query(Owner).filter_by(name=row['name']).first()
            if existing:
                owner = existing
                owner.description = row['description']
                owner.contact_info = row['contact_info']
            else:
                owner = Owner(
                    name=row['name'],
                    description=row['description'],
                    contact_info=row['contact_info']
                )
                session.add(owner)
                owner_count += 1
            
            # Commit to get owner.id
            session.commit()
            
            # First clear existing IP and domain records if updating
            if existing:
                session.query(OwnerIP).filter_by(owner_id=owner.id).delete()
                session.query(OwnerDomain).filter_by(owner_id=owner.id).delete()
            
            # Add IP addresses if present
            if row['ip_addresses']:
                for ip in row['ip_addresses'].split('|'):
                    if ip.strip():
                        # Determine if this is a CIDR range
                        is_cidr = '/' in ip.strip()
                        owner_ip = OwnerIP(
                            owner_id=owner.id,
                            ip=ip.strip(),
                            is_cidr=is_cidr
                        )
                        session.add(owner_ip)
                        ip_count += 1
            
            # Add domains if present
            if row['domains']:
                for domain in row['domains'].split('|'):
                    if domain.strip():
                        # Set include_subdomains based on whether it's a base domain or subdomain
                        # Base domains include subdomains, specific subdomains don't
                        include_subdomains = domain.strip().count('.') == 1  # example.com (1 dot) includes subdomains
                        owner_domain = OwnerDomain(
                            owner_id=owner.id,
                            domain=domain.strip(),
                            include_subdomains=include_subdomains
                        )
                        session.add(owner_domain)
                        domain_count += 1
            
            session.commit()
    
    print(f"Loaded {owner_count} owners with {ip_count} IP records and {domain_count} domain records from {filename}")

def load_services(filename):
    """Load services from CSV file."""
    filepath = os.path.join(SAMPLE_DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found")
        return
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        
        for row in reader:
            # Get fruit if specified
            fruit_id = None
            if row.get('fruit_id'):
                fruit = session.query(Fruit).filter_by(name=row['fruit_id']).first()
                if fruit:
                    fruit_id = fruit.id
            
            # Get owner if specified
            owner_id = None
            if row.get('owner_id'):
                owner = session.query(Owner).filter_by(name=row['owner_id']).first()
                if owner:
                    owner_id = owner.id
            
            # Create service
            service = Service(
                ip=row['ip'],
                port=int(row['port']),
                asn=row['asn'],
                country=row['country'],
                domain=row['domain'] if row['domain'] else None,
                banner_data=row['banner_data'] if row['banner_data'] else None,
                http_data=row['http_data'] if row['http_data'] else None,
                fruit_id=fruit_id,
                owner_id=owner_id
            )
            session.add(service)
            count += 1
    
    session.commit()
    print(f"Loaded {count} services from {filename}")

def load_recipes(filename):
    """Load recipes from CSV file"""
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            recipe = Recipe(
                name=row['name'],
                description=row['description'],
                instructions=row['instructions'],
                preparation_time=int(row['preparation_time'])
            )
            
            # Changed from fruit_types to fruits
            fruits = row['fruits'].split('|')
            for fruit_name in fruits:
                fruit = session.query(Fruit).filter_by(name=fruit_name.strip()).first()
                if fruit:
                    recipe.fruits.append(fruit)
                else:
                    print(f"Warning: Fruit {fruit_name} not found")
            
            session.add(recipe)
            count += 1
    
    session.commit()
    print(f"Loaded {count} recipes from {filename}")

def auto_assign_ownership(session):
    """
    Run automatic service ownership assignment based on IP and domain rules.
    This demonstrates the core functionality of the ownership matching system.
    """
    print("\nRunning automatic service ownership assignment...")
    
    # Count services before assignment
    total = session.query(Service).count()
    owned_before = session.query(Service).filter(Service.owner_id.isnot(None)).count()
    
    # Execute reassignment (clear and reassign all)
    # First clear all ownership
    session.query(Service).update({"owner_id": None}, synchronize_session=False)
    session.commit()
    
    # Process exact IP matches
    ip_matches = 0
    ip_rules = session.query(OwnerIP).filter_by(is_cidr=False).all()
    for rule in ip_rules:
        result = session.query(Service).filter_by(ip=rule.ip).update(
            {"owner_id": rule.owner_id},
            synchronize_session=False
        )
        ip_matches += result
    
    # Process CIDR ranges - this is more complex as we need to check each service
    cidr_matches = 0
    cidr_rules = session.query(OwnerIP).filter_by(is_cidr=True).all()
    services = session.query(Service).filter(Service.owner_id.is_(None)).all()
    
    for rule in cidr_rules:
        try:
            import ipaddress
            network = ipaddress.ip_network(rule.ip, strict=False)
            
            for service in services:
                try:
                    if service.owner_id is None and service.ip:
                        service_ip = ipaddress.ip_address(service.ip)
                        if service_ip in network:
                            service.owner_id = rule.owner_id
                            cidr_matches += 1
                except ValueError:
                    continue
        except ValueError:
            print(f"Warning: Invalid CIDR range: {rule.ip}")
            continue
    
    # Process domains
    domain_matches = 0
    subdomain_matches = 0
    
    # Exact domain matches
    domain_rules = session.query(OwnerDomain).all()
    for rule in domain_rules:
        # Exact matches first
        result = session.query(Service).filter(
            Service.owner_id.is_(None),
            Service.domain == rule.domain
        ).update(
            {"owner_id": rule.owner_id},
            synchronize_session=False
        )
        domain_matches += result
        
        # Subdomain matches for those with include_subdomains=True
        if rule.include_subdomains:
            # Select domains that end with .domain
            result = session.query(Service).filter(
                Service.owner_id.is_(None),
                Service.domain.isnot(None),
                Service.domain.like(f"%.{rule.domain}")
            ).update(
                {"owner_id": rule.owner_id},
                synchronize_session=False
            )
            subdomain_matches += result
    
    session.commit()
    
    # Count services after assignment
    owned_after = session.query(Service).filter(Service.owner_id.isnot(None)).count()
    
    print(f"Service Ownership Assignment Results:")
    print(f"- Total services: {total}")
    print(f"- Services with owners before: {owned_before}")
    print(f"- Services with owners after: {owned_after}")
    print(f"- Matched by IP address: {ip_matches}")
    print(f"- Matched by CIDR range: {cidr_matches}")
    print(f"- Matched by exact domain: {domain_matches}")
    print(f"- Matched by subdomain: {subdomain_matches}")
    print(f"- Total matched: {ip_matches + cidr_matches + domain_matches + subdomain_matches}")

def auto_identify_services(session):
    """
    Run automatic service identification based on fingerprints.
    This demonstrates the service fingerprinting functionality.
    """
    print("\nRunning automatic service identification...")
    
    # Count services before identification
    total = session.query(Service).count()
    identified_before = session.query(Service).filter(Service.fruit_id.isnot(None)).count()
    
    # Clear existing fruit associations and trigger re-identification
    session.query(Service).update({"fruit_id": None, "fruit_type_id": None}, synchronize_session=False)
    session.commit()
    
    # Manually run the fingerprinting for each service
    services = session.query(Service).all()
    matches_by_type = {}
    
    for service in services:
        # Try to match banner data first
        if service.banner_data:
            for fruit in session.query(Fruit).filter_by(match_type='banner').all():
                try:
                    import re
                    if re.search(fruit.match_regex, service.banner_data):
                        service.fruit_id = fruit.id
                        service.fruit_type_id = fruit.fruit_type_id
                        matches_by_type.setdefault('banner', 0)
                        matches_by_type['banner'] += 1
                        break
                except Exception:
                    continue
        
        # Try to match HTML content if available and not already matched
        if service.fruit_id is None and service.http_data:
            try:
                html_content = None
                if isinstance(service.http_data, str):
                    data = json.loads(service.http_data)
                    html_content = data.get('html')
                elif isinstance(service.http_data, dict):
                    html_content = service.http_data.get('html')
                
                if html_content:
                    for fruit in session.query(Fruit).filter_by(match_type='html').all():
                        try:
                            import re
                            if re.search(fruit.match_regex, html_content):
                                service.fruit_id = fruit.id
                                service.fruit_type_id = fruit.fruit_type_id
                                matches_by_type.setdefault('html', 0)
                                matches_by_type['html'] += 1
                                break
                        except Exception:
                            continue
            except Exception:
                pass
        
        # Try to match HTTP headers if available and not already matched
        if service.fruit_id is None and service.http_data:
            try:
                headers = None
                if isinstance(service.http_data, str):
                    data = json.loads(service.http_data)
                    headers = data.get('headers')
                elif isinstance(service.http_data, dict):
                    headers = service.http_data.get('headers')
                
                if headers:
                    header_str = ""
                    if isinstance(headers, dict):
                        for key, value in headers.items():
                            header_str += f"{key}: {value}\r\n"
                    elif isinstance(headers, str):
                        header_str = headers
                    
                    for fruit in session.query(Fruit).filter_by(match_type='http_header').all():
                        try:
                            import re
                            if re.search(fruit.match_regex, header_str):
                                service.fruit_id = fruit.id
                                service.fruit_type_id = fruit.fruit_type_id
                                matches_by_type.setdefault('http_header', 0)
                                matches_by_type['http_header'] += 1
                                break
                        except Exception:
                            continue
            except Exception:
                pass
        
        # Assign to unknown if no match
        if service.fruit_id is None:
            unknown = session.query(Fruit).filter_by(name="unknown").first()
            if unknown:
                service.fruit_id = unknown.id
                service.fruit_type_id = unknown.fruit_type_id
                matches_by_type.setdefault('unknown', 0)
                matches_by_type['unknown'] += 1
    
    session.commit()

def create_admin_user():
    """Create default admin user"""
    admin = User(
        username='admin3',
        email='admin3@example.com',
        password_hash=bcrypt.hash('admin123'),  # Change in production!
        is_admin=True
    )
    session.add(admin)
    
def init_db():
    """Initialize database with sample data"""
    # Create admin user
    create_admin_user()
    
    # Load sample data
    load_fruit_types('./sample_data/fruit_types.csv')
    load_fruits('./sample_data/fruits.csv')
    load_recipes('./sample_data/recipes.csv')
    load_owners('./sample_data/owners.csv')
    load_services('./sample_data/long_services.csv')
    auto_assign_ownership(session)
    auto_identify_services(session)

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")