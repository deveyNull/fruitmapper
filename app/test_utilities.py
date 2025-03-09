#!/usr/bin/env python3
"""
Utility functions for database management and testing in the Fruit Platform application.

This module provides helper functions to:
1. Populate test data
2. Clean database
3. Generate reports on ownership
4. Simulate network scanning results
"""

import os
import sys
import random
import ipaddress
import argparse
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func, desc, and_, or_, not_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from sqlalchemy.sql import expression


def case(whens, else_=None):
    """
    Create a SQL CASE expression.

    Args:
        whens: List of tuples (condition, result)
        else_: The else result

    Returns:
        An SQLAlchemy case expression
    """
    return expression.case(whens, else_=else_)

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

# Import models
from models import Base, User, FruitType, Fruit, Owner, OwnerIP, OwnerDomain, Service

# Database URL
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./app/fruit_platform.db")

def get_session(db_url=DB_URL):
    """Create and return a new database session."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()

def clean_database(db_url=DB_URL, confirm=True):
    """
    Clean the database by removing all data but keeping the structure.
    
    Args:
        db_url: Database URL
        confirm: Whether to ask for confirmation
    
    Returns:
        dict: Count of deleted records by table
    """
    if confirm:
        response = input("This will delete ALL data in the database. Are you sure? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return None
    
    engine = create_engine(db_url)
    session = sessionmaker(bind=engine)()
    
    # Order matters due to foreign key constraints
    deleted = {}
    
    # Delete all service records
    deleted['services'] = session.query(Service).delete()
    
    # Delete all ownership records
    deleted['owner_ips'] = session.query(OwnerIP).delete()
    deleted['owner_domains'] = session.query(OwnerDomain).delete()
    
    # Delete all fruits
    deleted['fruits'] = session.query(Fruit).delete()
    
    # Delete all fruit types
    deleted['fruit_types'] = session.query(FruitType).delete()
    
    # Delete all owners
    deleted['owners'] = session.query(Owner).delete()
    
    # Commit the changes
    session.commit()
    session.close()
    
    return deleted

def generate_random_cidr(base_network='192.168.0.0/16', prefix_length=24):
    """
    Generate a random CIDR subnet within a base network.
    
    Args:
        base_network: Base network to generate subnets from
        prefix_length: Length of the CIDR prefix (subnet mask)
    
    Returns:
        str: A random CIDR subnet
    """
    network = ipaddress.ip_network(base_network)
    
    # Calculate how many subnets we can create
    subnet_bits = prefix_length - network.prefixlen
    if subnet_bits <= 0:
        return str(network)
    
    max_subnets = 2 ** subnet_bits
    
    # Generate a random subnet index
    subnet_index = random.randint(0, max_subnets - 1)
    
    # Get the subnet
    subnets = list(network.subnets(new_prefix=prefix_length))
    if subnet_index < len(subnets):
        return str(subnets[subnet_index])
    else:
        return str(network)

def generate_random_ip(cidr):
    """
    Generate a random IP address within a CIDR range.
    
    Args:
        cidr: CIDR range to generate IP from
    
    Returns:
        str: A random IP address
    """
    network = ipaddress.ip_network(cidr)
    
    # Get the first and last IP in the range (excluding network and broadcast)
    if network.prefixlen < 31:  # Only exclude if not a /31 or /32
        first_ip = int(network.network_address) + 1
        last_ip = int(network.broadcast_address) - 1
    else:
        first_ip = int(network.network_address)
        last_ip = int(network.broadcast_address)
    
    if first_ip > last_ip:
        return str(network.network_address)
    
    # Generate a random IP in the range
    random_ip = random.randint(first_ip, last_ip)
    return str(ipaddress.ip_address(random_ip))

def generate_random_domain(base_domains=None, include_subdomains=True):
    """
    Generate a random domain name.
    
    Args:
        base_domains: List of base domains to use
        include_subdomains: Whether to include subdomains
    
    Returns:
        str: A random domain name
    """
    if base_domains is None:
        base_domains = [
            "example.com", "test.org", "demo.net", "sample.io", 
            "acme.co", "fruit.dev", "network.tech"
        ]
    
    domain = random.choice(base_domains)
    
    if include_subdomains and random.random() < 0.7:  # 70% chance of subdomain
        subdomains = ["www", "api", "app", "dev", "stage", "test", "beta", "admin", "mail", "blog"]
        subdomain = random.choice(subdomains)
        return f"{subdomain}.{domain}"
    
    return domain

def create_test_owners(session, count=5):
    """
    Create test owner organizations.
    
    Args:
        session: SQLAlchemy session
        count: Number of owners to create
    
    Returns:
        list: Created Owner objects"
    """
    
    owner_names = [
        "Acme Corporation", "Globex Technologies", "Initech Systems", 
        "Umbrella Corporation", "Stark Industries", "Wayne Enterprises",
        "Cyberdyne Systems", "Soylent Corp", "LexCorp", "Oscorp Industries"
    ]
    
    descriptions = [
        "Technology provider", "Network solutions", "Software development",
        "Security services", "Infrastructure management", "Cloud hosting",
        "Telecommunications", "Internet services", "Data analytics", "Consulting"
    ]
    
    owners = []
    for i in range(min(count, len(owner_names))):
        owner = Owner(
            name=owner_names[i],
            description=f"{random.choice(descriptions)} company",
            contact_info=f"contact@{owner_names[i].lower().replace(' ', '')}.com"
        )
        session.add(owner)
    
    session.commit()
    owners = session.query(Owner).all()
    print(f"Created {len(owners)} test owners")
    return owners

def assign_random_ip_ownership(session, owners, count_per_owner=3):
    """
    Assign random IP addresses and CIDR ranges to owners.
    
    Args:
        session: SQLAlchemy session
        owners: List of Owner objects
        count_per_owner: Number of IP/CIDR entries per owner
    
    Returns:
        dict: Counts of created records
    """
    results = {'single_ips': 0, 'cidr_ranges': 0}
    
    for owner in owners:
        # Add some individual IPs
        for _ in range(count_per_owner // 2):
            ip = generate_random_ip('10.0.0.0/8')  # Random IP in private range
            owner_ip = OwnerIP(
                owner_id=owner.id,
                ip=ip,
                is_cidr=False
            )
            session.add(owner_ip)
            results['single_ips'] += 1
        
        # Add some CIDR ranges
        for _ in range(count_per_owner - (count_per_owner // 2)):
            cidr = generate_random_cidr('172.16.0.0/12', 24)
            owner_ip = OwnerIP(
                owner_id=owner.id,
                ip=cidr,
                is_cidr=True
            )
            session.add(owner_ip)
            results['cidr_ranges'] += 1
    
    session.commit()
    print(f"Created {results['single_ips']} single IPs and {results['cidr_ranges']} CIDR ranges")
    return results

def assign_random_domain_ownership(session, owners, count_per_owner=2):
    """
    Assign random domains to owners.
    
    Args:
        session: SQLAlchemy session
        owners: List of Owner objects
        count_per_owner: Number of domains per owner
    
    Returns:
        dict: Counts of created records
    """
    results = {'domains': 0, 'with_subdomains': 0}
    
    base_domains = [
        "example.com", "test.org", "demo.net", "sample.io", 
        "acme.co", "fruit.dev", "network.tech", "company.biz",
        "service.app", "cloud.xyz"
    ]
    
    # Ensure we have enough domains for all owners
    while len(base_domains) < len(owners) * count_per_owner:
        base_domains.append(f"company{len(base_domains)}.com")
    
    # Shuffle the domains
    random.shuffle(base_domains)
    
    domain_index = 0
    for owner in owners:
        for _ in range(count_per_owner):
            if domain_index >= len(base_domains):
                break
                
            include_subdomains = random.random() < 0.7  # 70% chance of including subdomains
            
            owner_domain = OwnerDomain(
                owner_id=owner.id,
                domain=base_domains[domain_index],
                include_subdomains=include_subdomains
            )
            session.add(owner_domain)
            domain_index += 1
            
            results['domains'] += 1
            if include_subdomains:
                results['with_subdomains'] += 1
    
    session.commit()
    print(f"Created {results['domains']} domains ({results['with_subdomains']} with subdomain matching)")
    return results

def create_test_fruit_types(session):
    """
    Create basic fruit types for testing.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        list: Created FruitType objects
    """
    # Check if there are existing fruit types
    existing = session.query(FruitType).all()
    if existing:
        print(f"Using {len(existing)} existing fruit types")
        return existing
    
    fruit_types = [
        FruitType(name="web-server", description="Web servers"),
        FruitType(name="database", description="Database servers"),
        FruitType(name="mail-server", description="Mail servers"),
        FruitType(name="proxy", description="Proxy servers"),
        FruitType(name="unknown", description="Unknown server types")
    ]
    
    session.add_all(fruit_types)
    session.commit()
    
    print(f"Created {len(fruit_types)} fruit types")
    return fruit_types

def create_test_fruits(session, fruit_types):
    """
    Create test fruits based on fruit types.
    
    Args:
        session: SQLAlchemy session
        fruit_types: List of FruitType objects
    
    Returns:
        list: Created Fruit objects
    """
    # Define specific fruits for each type
    fruits_by_type = {
        "web-server": [
            {"name": "nginx", "match_type": "banner", "match_regex": "nginx"},
            {"name": "apache", "match_type": "banner", "match_regex": "Apache"},
            {"name": "iis", "match_type": "banner", "match_regex": "Microsoft-IIS"}
        ],
        "database": [
            {"name": "mysql", "match_type": "banner", "match_regex": "mysql"},
            {"name": "postgresql", "match_type": "banner", "match_regex": "PostgreSQL"},
            {"name": "mssql", "match_type": "banner", "match_regex": "Microsoft SQL Server"}
        ],
        "mail-server": [
            {"name": "exchange", "match_type": "banner", "match_regex": "Microsoft Exchange"},
            {"name": "postfix", "match_type": "banner", "match_regex": "Postfix"},
            {"name": "sendmail", "match_type": "banner", "match_regex": "Sendmail"}
        ],
        "proxy": [
            {"name": "squid", "match_type": "banner", "match_regex": "squid"},
            {"name": "haproxy", "match_type": "banner", "match_regex": "HAProxy"},
            {"name": "nginx-proxy", "match_type": "banner", "match_regex": "nginx.*proxy"}
        ],
        "unknown": [
            {"name": "unknown", "match_type": "unknown", "match_regex": "unknown"}
        ]
    }
    
    all_fruits = []
    
    # Create fruits for each type
    for fruit_type in fruit_types:
        type_name = fruit_type.name
        if type_name in fruits_by_type:
            for fruit_data in fruits_by_type[type_name]:
                fruit = Fruit(
                    name=fruit_data["name"],
                    date_picked=datetime.utcnow(),
                    fruit_type_id=fruit_type.id,
                    match_type=fruit_data["match_type"],
                    match_regex=fruit_data["match_regex"]
                )
                session.add(fruit)
                all_fruits.append(fruit)
    
    session.commit()
    print(f"Created {len(all_fruits)} fruits")
    return all_fruits

def create_test_services(session, count=100, with_ownership=True):
    """
    Create test services with random properties.
    
    Args:
        session: SQLAlchemy session
        count: Number of services to create
        with_ownership: Whether to attempt to match with existing ownership rules
    
    Returns:
        dict: Statistics about created services
    """
    stats = {
        'total': 0,
        'with_domain': 0,
        'with_owner': 0,
        'by_fruit_type': {}
    }
    
    # Get available fruits
    fruits = session.query(Fruit).all()
    if not fruits:
        print("No fruits available. Creating default fruits...")
        fruit_types = create_test_fruit_types(session)
        fruits = create_test_fruits(session, fruit_types)
    
    # Group fruits by type for better distribution
    fruits_by_type = {}
    for fruit in fruits:
        type_id = fruit.fruit_type_id
        if type_id not in fruits_by_type:
            fruits_by_type[type_id] = []
        fruits_by_type[type_id].append(fruit)
    
    # Initialize stats counters
    for type_id in fruits_by_type:
        fruit_type = session.query(FruitType).get(type_id)
        if fruit_type:
            stats['by_fruit_type'][fruit_type.name] = 0
    
    # Create services
    for _ in range(count):
        # Select a random fruit type with higher probability for web servers
        weights = [3 if t.name == 'web-server' else 1 for t in session.query(FruitType).all()]
        fruit_type = random.choices(session.query(FruitType).all(), weights=weights, k=1)[0]
        
        # Select a random fruit of that type
        if fruit_type.id in fruits_by_type and fruits_by_type[fruit_type.id]:
            fruit = random.choice(fruits_by_type[fruit_type.id])
        else:
            # Fallback to unknown if no fruits for this type
            unknown_type = session.query(FruitType).filter_by(name="unknown").first()
            if unknown_type and unknown_type.id in fruits_by_type:
                fruit = random.choice(fruits_by_type[unknown_type.id])
            else:
                # If still no fruit, use the first one available
                fruit = fruits[0]
        
        # Generate IP address
        networks = ['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']
        ip = generate_random_ip(random.choice(networks))
        
        # Generate port number (prefer common ports)
        common_ports = [80, 443, 22, 25, 587, 110, 143, 3306, 5432, 1433, 8080, 8443]
        if random.random() < 0.8:  # 80% chance of common port
            port = random.choice(common_ports)
        else:
            port = random.randint(1024, 65535)
        
        # Generate domain (50% chance)
        domain = None
        if random.random() < 0.5:
            domain = generate_random_domain()
            stats['with_domain'] += 1
        
        # Generate banner data
        if fruit.match_type == 'banner':
            # Create banner with the matching pattern to ensure it can be matched
            banner_templates = {
                "nginx": "Server: nginx/1.18.0\r\nDate: {date}\r\n",
                "apache": "Server: Apache/2.4.41 (Ubuntu)\r\nDate: {date}\r\n",
                "iis": "Server: Microsoft-IIS/10.0\r\nDate: {date}\r\n",
                "mysql": "MySQL server version 8.0.23\r\n",
                "postgresql": "PostgreSQL 13.3 on x86_64-pc-linux-gnu\r\n",
                "mssql": "Microsoft SQL Server 2019 (RTM) - 15.0.2000.5\r\n",
                "exchange": "Microsoft Exchange Server 2019\r\n",
                "postfix": "Postfix SMTP server ready\r\n",
                "sendmail": "Sendmail 8.15.2\r\n",
                "squid": "Squid/4.13\r\n",
                "haproxy": "HAProxy 2.4.0\r\n",
                "nginx-proxy": "nginx/1.18.0 (Ubuntu) proxy\r\n"
            }
            
            if fruit.name in banner_templates:
                banner = banner_templates[fruit.name].format(
                    date=datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
                )
            else:
                banner = f"Generic banner with {fruit.match_regex} inside\r\n"
        else:
            banner = "Unknown server\r\n"
        
        # Create the service
        service = Service(
            ip=ip,
            port=port,
            domain=domain,
            asn=f"AS{random.randint(1000, 65000)}",
            country=random.choice(['US', 'UK', 'DE', 'FR', 'JP', 'AU', 'CA', 'BR']),
            banner_data=banner,
            fruit_id=fruit.id,
            fruit_type_id=fruit.fruit_type_id
        )
        
        session.add(service)
        stats['total'] += 1
        
        # Count by fruit type
        if fruit.fruit_type.name in stats['by_fruit_type']:
            stats['by_fruit_type'][fruit.fruit_type.name] += 1
    
    # Commit to ensure all services are in the database
    session.commit()
    
    # If with_ownership is True, try to match services with existing ownership rules
    if with_ownership:
        reassign_services(session)
        
        # Count services with owners
        with_owner = session.query(Service).filter(Service.owner_id.isnot(None)).count()
        stats['with_owner'] = with_owner
    
    print(f"Created {stats['total']} services ({stats['with_domain']} with domains, {stats['with_owner']} with owners)")
    for fruit_type, count in stats['by_fruit_type'].items():
        print(f"  - {fruit_type}: {count} services")
    
    return stats

def reassign_services(session):
    """
    Reassign all services based on current ownership rules.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        dict: Statistics about reassignment
    """
    stats = {
        'total': 0,
        'ip_matches': 0,
        'cidr_matches': 0,
        'domain_matches': 0,
        'subdomain_matches': 0
    }
    
    # Get all services
    services = session.query(Service).all()
    stats['total'] = len(services)
    
    # Get all ownership rules
    ip_rules = session.query(OwnerIP).filter_by(is_cidr=False).all()
    cidr_rules = session.query(OwnerIP).filter_by(is_cidr=True).all()
    
    exact_domain_rules = session.query(OwnerDomain).all()
    subdomain_rules = session.query(OwnerDomain).filter_by(include_subdomains=True).all()
    
    # Process each service
    for service in services:
        old_owner_id = service.owner_id
        
        # Try exact IP match first
        if service.ip:
            for rule in ip_rules:
                if service.ip == rule.ip:
                    service.owner_id = rule.owner_id
                    stats['ip_matches'] += 1
                    break
        
        # Try CIDR match if no exact match and ownership not yet determined
        if service.ip and service.owner_id == old_owner_id:
            try:
                ip_obj = ipaddress.ip_address(service.ip)
                for rule in cidr_rules:
                    try:
                        network = ipaddress.ip_network(rule.ip, strict=False)
                        if ip_obj in network:
                            service.owner_id = rule.owner_id
                            stats['cidr_matches'] += 1
                            break
                    except ValueError:
                        continue
            except ValueError:
                pass
        
        # Try exact domain match if ownership not yet determined
        if service.domain and service.owner_id == old_owner_id:
            for rule in exact_domain_rules:
                if service.domain == rule.domain:
                    service.owner_id = rule.owner_id
                    stats['domain_matches'] += 1
                    break
        
        # Try subdomain match if ownership not yet determined
        if service.domain and service.owner_id == old_owner_id:
            for rule in subdomain_rules:
                if rule.domain and service.domain.endswith('.' + rule.domain):
                    service.owner_id = rule.owner_id
                    stats['subdomain_matches'] += 1
                    break
    
    session.commit()
    
    # Get total with owners after reassignment
    with_owner = session.query(Service).filter(Service.owner_id.isnot(None)).count()
    stats['with_owner'] = with_owner
    
    print(f"Reassigned {with_owner} services:")
    print(f"  - IP matches: {stats['ip_matches']}")
    print(f"  - CIDR matches: {stats['cidr_matches']}")
    print(f"  - Domain matches: {stats['domain_matches']}")
    print(f"  - Subdomain matches: {stats['subdomain_matches']}")
    
    return stats

def generate_ownership_report(session):
    """
    Generate a report on service ownership.
    
    Args:
        session: SQLAlchemy session
    
    Returns:
        dict: Report statistics
    """
    report = {
        'total_services': 0,
        'owned_services': 0,
        'unowned_services': 0,
        'ownership_percentage': 0,
        'by_owner': [],
        'by_fruit_type': []
    }
    
    # Count total and owned services
    total = session.query(func.count(Service.id)).scalar() or 0
    owned = session.query(func.count(Service.id)).filter(Service.owner_id.isnot(None)).scalar() or 0
    unowned = total - owned
    
    report['total_services'] = total
    report['owned_services'] = owned
    report['unowned_services'] = unowned
    report['ownership_percentage'] = (owned / total * 100) if total > 0 else 0
    
    # Services by owner
    owner_stats = session.query(
        Owner.id,
        Owner.name,
        func.count(Service.id).label('service_count')
    ).outerjoin(
        Service, Owner.id == Service.owner_id
    ).group_by(
        Owner.id
    ).order_by(
        desc('service_count')
    ).all()
    
    for owner_id, owner_name, service_count in owner_stats:
        report['by_owner'].append({
            'owner_id': owner_id,
            'owner_name': owner_name,
            'service_count': service_count,
            'percentage': (service_count / total * 100) if total > 0 else 0
        })
    
    # Services by fruit type
    fruit_type_stats = session.query(
        FruitType.id,
        FruitType.name,
        func.count(Service.id).label('service_count'),
        func.sum(case([(Service.owner_id.isnot(None), 1)], else_=0)).label('owned_count')
    ).join(
        Service, FruitType.id == Service.fruit_type_id
    ).group_by(
        FruitType.id
    ).order_by(
        desc('service_count')
    ).all()
    
    for type_id, type_name, service_count, owned_count in fruit_type_stats:
        ownership_rate = (owned_count / service_count * 100) if service_count > 0 else 0
        report['by_fruit_type'].append({
            'type_id': type_id,
            'type_name': type_name,
            'service_count': service_count,
            'percentage_of_total': (service_count / total * 100) if total > 0 else 0,
            'owned_count': owned_count,
            'ownership_rate': ownership_rate
        })
    
    # Print summary report
    print("\n--- OWNERSHIP REPORT ---")
    print(f"Total Services: {report['total_services']}")
    print(f"Owned Services: {report['owned_services']} ({report['ownership_percentage']:.1f}%)")
    print(f"Unowned Services: {report['unowned_services']}")
    
    print("\nTop Owners:")
    for idx, owner in enumerate(report['by_owner'][:5], 1):
        if owner['service_count'] > 0:
            print(f"{idx}. {owner['owner_name']}: {owner['service_count']} services ({owner['percentage']:.1f}%)")
    
    print("\nBy Fruit Type:")
    for idx, fruit_type in enumerate(report['by_fruit_type'], 1):
        print(f"{idx}. {fruit_type['type_name']}: {fruit_type['service_count']} services, {fruit_type['owned_count']} owned ({fruit_type['ownership_rate']:.1f}%)")
    
    return report

def populate_test_data(session, config=None):
    """
    Populate test data for the application.
    
    Args:
        session: SQLAlchemy session
        config: Configuration dictionary with counts
    
    Returns:
        dict: Statistics about created data
    """
    if config is None:
        config = {
            'owners': 5,
            'ips_per_owner': 3,
            'domains_per_owner': 2,
            'services': 100
        }
    
    stats = {
        'fruit_types': 0,
        'fruits': 0,
        'owners': 0,
        'ips': 0,
        'domains': 0,
        'services': 0
    }
    
    # Create fruit types and fruits
    fruit_types = create_test_fruit_types(session)
    stats['fruit_types'] = len(fruit_types)
    
    fruits = create_test_fruits(session, fruit_types)
    stats['fruits'] = len(fruits)
    
    # Create owners
    owners = create_test_owners(session, config['owners'])
    stats['owners'] = len(owners)
    
    # Assign IP ownership
    ip_results = assign_random_ip_ownership(session, owners, config['ips_per_owner'])
    stats['ips'] = ip_results['single_ips'] + ip_results['cidr_ranges']
    
    # Assign domain ownership
    domain_results = assign_random_domain_ownership(session, owners, config['domains_per_owner'])
    stats['domains'] = domain_results['domains']
    
    # Create services
    service_results = create_test_services(session, config['services'], with_ownership=True)
    stats['services'] = service_results['total']
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='Database utilities for the Fruit Platform application')
    parser.add_argument('action', choices=['clean', 'populate', 'report', 'reassign', 'test'], 
                      help='Action to perform')
    parser.add_argument('--db', type=str, default=DB_URL, 
                      help='Database URL')
    parser.add_argument('--owners', type=int, default=5, 
                      help='Number of owner organizations to create')
    parser.add_argument('--services', type=int, default=100, 
                      help='Number of services to create')
    parser.add_argument('--force', action='store_true', 
                      help='Skip confirmation for destructive actions')
    
    args = parser.parse_args()
    
    session = get_session(args.db)
    
    try:
        if args.action == 'clean':
            results = clean_database(args.db, confirm=not args.force)
            if results:
                print("Database cleaned successfully")
                for table, count in results.items():
                    print(f"  - {table}: {count} records deleted")
        
        elif args.action == 'populate':
            config = {
                'owners': args.owners,
                'ips_per_owner': 3,
                'domains_per_owner': 2,
                'services': args.services
            }
            stats = populate_test_data(session, config)
            print("\nPopulated database with test data:")
            for category, count in stats.items():
                print(f"  - {category}: {count}")
        
        elif args.action == 'report':
            generate_ownership_report(session)
        
        elif args.action == 'reassign':
            reassign_services(session)
        
        elif args.action == 'test':
            # Import and run the ownership tester
            from test_owner_matching import OwnershipTester
            tester = OwnershipTester(args.db)
            tester.run_all_tests()
    
    finally:
        session.close()

if __name__ == "__main__":
    main()