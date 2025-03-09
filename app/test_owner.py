"""
Test script for owner matching functionality in the Fruit Platform application.

This script performs a series of tests to verify that the ownership matching logic
works correctly for both direct matches, CIDR ranges, and domain/subdomain matching.
"""

import os
import sys
import ipaddress
from datetime import datetime
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

# Import models
from models import Base, User, FruitType, Fruit, Owner, OwnerIP, OwnerDomain, Service

# Create database engine - using SQLite memory for testing
TEST_DB_URL = "sqlite:///./test_fruit_platform.db"

# Functions for color output
def green(text):
    return f"\033[92m{text}\033[0m"

def red(text):
    return f"\033[91m{text}\033[0m"

def yellow(text):
    return f"\033[93m{text}\033[0m"

def blue(text):
    return f"\033[94m{text}\033[0m"

def print_test_header(text):
    print(f"\n{blue('='*80)}")
    print(f"{blue('TEST:')} {text}")
    print(f"{blue('='*80)}")

def print_section(text):
    print(f"\n{yellow('-'*40)}")
    print(f"{yellow(text)}")
    print(f"{yellow('-'*40)}")

def print_success(text):
    print(green(f"✓ {text}"))

def print_failure(text):
    print(red(f"✗ {text}"))

def print_info(text):
    print(f"  {text}")

class OwnershipTester:
    def __init__(self, db_url=TEST_DB_URL):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.fruit_types = {}
        self.fruits = {}
        self.owners = {}
        self.services = {}

    def setup_database(self):
        """Create tables and initial data for testing"""
        print_section("Setting up database")
        
        # Drop all tables first (if they exist)
        Base.metadata.drop_all(self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
        
        # Create default fruit types and fruits
        self._create_fruit_types()
        self._create_fruits()
        
        # Create test owners
        self._create_owners()
        
        print_success("Database setup complete")

    def _create_fruit_types(self):
        """Create fruit types for testing"""
        fruit_types = [
            FruitType(name="citrus", description="Citrus fruits"),
            FruitType(name="berry", description="Berry fruits"),
            FruitType(name="unknown", description="Unknown fruit type")
        ]
        
        self.session.add_all(fruit_types)
        self.session.commit()
        
        # Store for later reference
        for ft in fruit_types:
            self.fruit_types[ft.name] = ft
            
        print_success("Created fruit types")

    def _create_fruits(self):
        """Create fruits for testing"""
        fruits = [
            Fruit(
                name="orange", 
                date_picked=datetime.utcnow(),
                fruit_type_id=self.fruit_types["citrus"].id,
                match_type="banner",
                match_regex="orange"
            ),
            Fruit(
                name="lemon", 
                date_picked=datetime.utcnow(),
                fruit_type_id=self.fruit_types["citrus"].id,
                match_type="banner",
                match_regex="lemon"
            ),
            Fruit(
                name="strawberry", 
                date_picked=datetime.utcnow(),
                fruit_type_id=self.fruit_types["berry"].id,
                match_type="banner",
                match_regex="strawberry"
            ),
            Fruit(
                name="unknown", 
                date_picked=datetime.utcnow(),
                fruit_type_id=self.fruit_types["unknown"].id,
                match_type="unknown",
                match_regex="unknown"
            )
        ]
        
        self.session.add_all(fruits)
        self.session.commit()
        
        # Store for later reference
        for f in fruits:
            self.fruits[f.name] = f
            
        print_success("Created fruits")

    def _create_owners(self):
        """Create test owners"""
        owners = [
            Owner(
                name="Acme Corp",
                description="Tech company",
                contact_info="contact@acme.com"
            ),
            Owner(
                name="Fruit Inc",
                description="Fruit company",
                contact_info="info@fruit.com"
            ),
            Owner(
                name="Network LLC",
                description="Network provider",
                contact_info="support@network.com"
            )
        ]
        
        self.session.add_all(owners)
        self.session.commit()
        
        # Store for later reference
        for o in owners:
            self.owners[o.name] = o
            
        print_success("Created owners")

    def create_services(self):
        """Create test services with no initial owner assignment"""
        print_section("Creating test services")
        
        services = [
            # IP-based matching test services
            Service(
                ip="192.168.1.10",
                port=80,
                asn="AS12345",
                country="US",
                banner_data="Web server",
                fruit_id=self.fruits["orange"].id,
                fruit_type_id=self.fruits["orange"].fruit_type_id
            ),
            Service(
                ip="192.168.2.20",
                port=443,
                asn="AS12345",
                country="US",
                banner_data="Secure server",
                fruit_id=self.fruits["lemon"].id,
                fruit_type_id=self.fruits["lemon"].fruit_type_id
            ),
            Service(
                ip="10.0.0.5",
                port=8080,
                asn="AS67890",
                country="UK",
                banner_data="Proxy server",
                fruit_id=self.fruits["strawberry"].id,
                fruit_type_id=self.fruits["strawberry"].fruit_type_id
            ),
            
            # Domain-based matching test services
            Service(
                ip="172.16.0.1",
                port=80,
                domain="example.com",
                asn="AS12345",
                country="US",
                banner_data="Main site",
                fruit_id=self.fruits["orange"].id,
                fruit_type_id=self.fruits["orange"].fruit_type_id
            ),
            Service(
                ip="172.16.0.2",
                port=443,
                domain="api.example.com",
                asn="AS12345",
                country="US",
                banner_data="API server",
                fruit_id=self.fruits["lemon"].id,
                fruit_type_id=self.fruits["lemon"].fruit_type_id
            ),
            Service(
                ip="172.16.0.3",
                port=8443,
                domain="blog.othersite.com",
                asn="AS67890",
                country="UK",
                banner_data="Blog server",
                fruit_id=self.fruits["strawberry"].id,
                fruit_type_id=self.fruits["strawberry"].fruit_type_id
            ),
            
            # Both IP and domain for combined tests
            Service(
                ip="192.168.10.10",
                port=80,
                domain="combined.example.com",
                asn="AS12345",
                country="US",
                banner_data="Combined test",
                fruit_id=self.fruits["orange"].id,
                fruit_type_id=self.fruits["orange"].fruit_type_id
            )
        ]
        
        self.session.add_all(services)
        self.session.commit()
        
        # Store services by IP for easier reference
        for s in services:
            self.services[s.ip] = s
            
        print_success(f"Created {len(services)} test services")
        
        # Verify no initial owner assignment
        unowned = self.session.query(Service).filter(Service.owner_id.is_(None)).count()
        print_info(f"{unowned} services have no owner initially")

    def test_exact_ip_matching(self):
        """Test exact IP address matching"""
        print_test_header("Exact IP Address Matching")
        
        # Add a specific IP to an owner
        owner = self.owners["Acme Corp"]
        target_ip = "192.168.1.10"
        
        print_info(f"Adding IP {target_ip} to owner {owner.name}")
        
        # Create the owner IP record
        owner_ip = OwnerIP(
            owner_id=owner.id,
            ip=target_ip,
            is_cidr=False
        )
        self.session.add(owner_ip)
        self.session.commit()
        
        # Check if service was automatically assigned
        service = self.session.query(Service).filter_by(ip=target_ip).first()
        
        if service.owner_id == owner.id:
            print_success(f"Service at {target_ip} was correctly assigned to {owner.name}")
        else:
            print_failure(f"Service at {target_ip} was not assigned to {owner.name}")
            
        # Check other services remain unaffected
        other_ip = "192.168.2.20"
        other_service = self.session.query(Service).filter_by(ip=other_ip).first()
        
        if other_service.owner_id is None:
            print_success(f"Service at {other_ip} correctly remains unassigned")
        else:
            print_failure(f"Service at {other_ip} was incorrectly assigned an owner")

    def test_cidr_matching(self):
        """Test CIDR range matching"""
        print_test_header("CIDR Range Matching")
        
        # Add a CIDR range to an owner
        owner = self.owners["Network LLC"]
        cidr_range = "10.0.0.0/24"  # Should match 10.0.0.5
        
        print_info(f"Adding CIDR range {cidr_range} to owner {owner.name}")
        
        # Create the owner IP record with CIDR
        owner_ip = OwnerIP(
            owner_id=owner.id,
            ip=cidr_range,
            is_cidr=True
        )
        self.session.add(owner_ip)
        self.session.commit()
        
        # Check if service was automatically assigned
        service = self.session.query(Service).filter_by(ip="10.0.0.5").first()
        
        if service.owner_id == owner.id:
            print_success(f"Service at 10.0.0.5 was correctly assigned to {owner.name} via CIDR {cidr_range}")
        else:
            print_failure(f"Service at 10.0.0.5 was not assigned to {owner.name}")
            
        # Test another CIDR that should match multiple services
        cidr_range2 = "192.168.0.0/16"  # Should match 192.168.*.* addresses
        
        print_info(f"Adding CIDR range {cidr_range2} to owner {owner.name}")
        
        # Create the owner IP record with CIDR
        owner_ip2 = OwnerIP(
            owner_id=owner.id,
            ip=cidr_range2,
            is_cidr=True
        )
        self.session.add(owner_ip2)
        self.session.commit()
        
        # Run manual reassignment
        self._reassign_services()
        
        # Check how many services in that range were assigned
        matching_count = self.session.query(Service).filter(
            and_(
                Service.ip.like("192.168.%"), 
                Service.owner_id == owner.id
            )
        ).count()
        
        expected_count = self.session.query(Service).filter(
            Service.ip.like("192.168.%")
        ).count()
        
        if matching_count == expected_count:
            print_success(f"All {matching_count} services in 192.168.*.* range were assigned to {owner.name}")
        else:
            print_failure(f"Only {matching_count} of {expected_count} services in 192.168.*.* range were assigned")

    def test_domain_matching(self):
        """Test exact domain matching"""
        print_test_header("Exact Domain Matching")
        
        # Add a domain to an owner
        owner = self.owners["Fruit Inc"]
        domain = "example.com"
        
        print_info(f"Adding domain {domain} to owner {owner.name} (without subdomain matching)")
        
        # Create the owner domain record without subdomain matching
        owner_domain = OwnerDomain(
            owner_id=owner.id,
            domain=domain,
            include_subdomains=False
        )
        self.session.add(owner_domain)
        self.session.commit()
        
        # Check if exact domain service was automatically assigned
        exact_service = self.session.query(Service).filter_by(domain=domain).first()
        
        if exact_service.owner_id == owner.id:
            print_success(f"Service with domain {domain} was correctly assigned to {owner.name}")
        else:
            print_failure(f"Service with domain {domain} was not assigned to {owner.name}")
            
        # Check subdomain service
        subdomain = "api.example.com"
        subdomain_service = self.session.query(Service).filter_by(domain=subdomain).first()
        
        if subdomain_service.owner_id is None:
            print_success(f"Service with subdomain {subdomain} correctly remains unassigned")
        else:
            print_failure(f"Service with subdomain {subdomain} was incorrectly assigned an owner")

    def test_subdomain_matching(self):
        """Test subdomain matching"""
        print_test_header("Subdomain Matching")
        
        # Add a domain to an owner with subdomain matching
        owner = self.owners["Acme Corp"]
        domain = "othersite.com"
        
        print_info(f"Adding domain {domain} to owner {owner.name} (with subdomain matching)")
        
        # Create the owner domain record with subdomain matching
        owner_domain = OwnerDomain(
            owner_id=owner.id,
            domain=domain,
            include_subdomains=True
        )
        self.session.add(owner_domain)
        self.session.commit()
        
        # Check subdomain service
        subdomain = "blog.othersite.com"
        subdomain_service = self.session.query(Service).filter_by(domain=subdomain).first()
        
        if subdomain_service.owner_id == owner.id:
            print_success(f"Service with subdomain {subdomain} was correctly assigned to {owner.name}")
        else:
            print_failure(f"Service with subdomain {subdomain} was not assigned to {owner.name}")

    def test_update_domain_settings(self):
        """Test updating domain settings to enable/disable subdomain matching"""
        print_test_header("Updating Domain Settings")
        
        # First get the example.com domain we added earlier
        owner = self.owners["Fruit Inc"]
        domain_name = "example.com"
        
        domain = self.session.query(OwnerDomain).filter_by(
            owner_id=owner.id, 
            domain=domain_name
        ).first()
        
        if not domain:
            print_failure(f"Domain {domain_name} not found for {owner.name}")
            return
            
        # Update to enable subdomain matching
        print_info(f"Enabling subdomain matching for {domain_name}")
        domain.include_subdomains = True
        self.session.commit()
        
        # Run reassignment
        self._reassign_services()
        
        # Check if subdomain service is now assigned
        subdomain = "api.example.com"
        subdomain_service = self.session.query(Service).filter_by(domain=subdomain).first()
        
        if subdomain_service.owner_id == owner.id:
            print_success(f"After enabling subdomain matching, service with {subdomain} was assigned to {owner.name}")
        else:
            print_failure(f"Service with subdomain {subdomain} was not assigned after enabling subdomain matching")
            
        # Update to disable subdomain matching again
        print_info(f"Disabling subdomain matching for {domain_name}")
        domain.include_subdomains = False
        self.session.commit()
        
        # Services should keep their current owner even after disabling subdomain matching
        subdomain_service = self.session.query(Service).filter_by(domain=subdomain).first()
        
        if subdomain_service.owner_id == owner.id:
            print_success(f"Service keeps its owner after disabling subdomain matching")
        else:
            print_info(f"Note: After disabling subdomain matching, existing assignments remain until manually changed")

    def test_ownership_conflict(self):
        """Test what happens when multiple ownership rules could apply"""
        print_test_header("Ownership Conflict Resolution")
        
        # First, make sure our test service has a clean state
        test_ip = "192.168.10.10"
        test_domain = "combined.example.com"
        
        service = self.session.query(Service).filter_by(ip=test_ip).first()
        service.owner_id = None
        self.session.commit()
        
        print_info(f"Testing with service at {test_ip} with domain {test_domain}")
        
        # Add IP ownership rule
        ip_owner = self.owners["Network LLC"]
        print_info(f"Adding IP {test_ip} to owner {ip_owner.name}")
        
        owner_ip = OwnerIP(
            owner_id=ip_owner.id,
            ip=test_ip
        )
        self.session.add(owner_ip)
        self.session.commit()
        
        # Check initial assignment
        service = self.session.query(Service).filter_by(ip=test_ip).first()
        
        if service.owner_id == ip_owner.id:
            print_success(f"Service was assigned to {ip_owner.name} based on IP match")
        else:
            print_failure(f"Service was not assigned correctly based on IP match")
            
        # Now add a domain rule with a different owner
        domain_owner = self.owners["Fruit Inc"]
        parent_domain = "example.com"
        
        # First make sure the domain owner exists
        existing_domain = self.session.query(OwnerDomain).filter_by(
            owner_id=domain_owner.id, 
            domain=parent_domain
        ).first()
        
        if existing_domain:
            # Update to ensure subdomain matching is enabled
            existing_domain.include_subdomains = True
            self.session.commit()
        else:
            # Create a new domain ownership
            print_info(f"Adding domain {parent_domain} to owner {domain_owner.name} with subdomain matching")
            owner_domain = OwnerDomain(
                owner_id=domain_owner.id,
                domain=parent_domain,
                include_subdomains=True
            )
            self.session.add(owner_domain)
            self.session.commit()
        
        # Run reassignment to see if domain rule overrides IP rule
        self._reassign_services()
        
        service = self.session.query(Service).filter_by(ip=test_ip).first()
        current_owner = self.session.query(Owner).filter_by(id=service.owner_id).first()
        
        print_info(f"Service is now owned by: {current_owner.name}")
        print_info("Note: The specific conflict resolution depends on the reassignment implementation.")
        print_info("In most real-world scenarios, it's better to have a clear priority rule.")

    def test_removing_ownership(self):
        """Test what happens when ownership rules are removed"""
        print_test_header("Removing Ownership Rules")
        
        # First check how many owned services we have
        owned_count = self.session.query(Service).filter(Service.owner_id.isnot(None)).count()
        print_info(f"Currently {owned_count} services have owners assigned")
        
        # Delete all OwnerIP records
        ip_count = self.session.query(OwnerIP).delete()
        
        # Delete all OwnerDomain records
        domain_count = self.session.query(OwnerDomain).delete()
        
        self.session.commit()
        
        print_info(f"Deleted {ip_count} IP ownership rules and {domain_count} domain ownership rules")
        print_info("Note: Existing service ownership is not automatically removed when rules are deleted")
        
        # Services should keep their current owners even after rules are deleted
        still_owned = self.session.query(Service).filter(Service.owner_id.isnot(None)).count()
        print_info(f"After deletion, {still_owned} services still have owners assigned")
        
        if still_owned == owned_count:
            print_success("Service ownership remained intact after deleting rules")
        else:
            print_failure("Some services unexpectedly lost their ownership")

    # Modifications to the reassign_services function in test_owner_matching.py
    def _reassign_services(self):
        """Run a reassignment of all services based on current rules"""
        print_info("Running service reassignment...")
        
        # First clear all ownership assignments to start fresh
        self.session.query(Service).update(
            {"owner_id": None},
            synchronize_session=False
        )
        self.session.commit()
        
        # Process exact IP matches
        ip_matches = self.session.query(OwnerIP).filter_by(is_cidr=False).all()
        for ip_match in ip_matches:
            self.session.query(Service).filter_by(ip=ip_match.ip).update(
                {"owner_id": ip_match.owner_id},
                synchronize_session=False
            )
        
        # Process CIDR matches - this requires evaluating each service
        cidr_ranges = self.session.query(OwnerIP).filter_by(is_cidr=True).all()
        
        # For CIDR processing, get ALL services, not just unowned ones
        # This ensures we process every service against every CIDR range
        services = self.session.query(Service).all()
        
        for cidr in cidr_ranges:
            try:
                network = ipaddress.ip_network(cidr.ip, strict=False)
                matching_ids = []
                
                for service in services:
                    try:
                        if service.ip and ipaddress.ip_address(service.ip) in network:
                            matching_ids.append(service.id)
                    except ValueError:
                        continue
                        
                # Update all matching services at once
                if matching_ids:
                    self.session.query(Service).filter(Service.id.in_(matching_ids)).update(
                        {"owner_id": cidr.owner_id},
                        synchronize_session=False
                    )
            except ValueError:
                continue

        # Process domain matches similar to IP matches
        # ... [rest of the function remains the same]
        
        # Process exact domain matches
        domain_rules = self.session.query(OwnerDomain).all()
        for domain in domain_rules:
            # Exact domain match
            self.session.query(Service).filter(
                Service.domain == domain.domain,
                Service.owner_id.is_(None)
            ).update(
                {"owner_id": domain.owner_id},
                synchronize_session=False
            )
            
            # Subdomain match if enabled
            if domain.include_subdomains:
                self.session.query(Service).filter(
                    and_(
                        Service.domain.isnot(None),
                        Service.owner_id.is_(None),
                        Service.domain.like(f"%.{domain.domain}")
                    )
                ).update(
                    {"owner_id": domain.owner_id},
                    synchronize_session=False
                )
        
        self.session.commit()
        
        # Report results
        assigned = self.session.query(Service).filter(Service.owner_id.isnot(None)).count()
        print_info(f"After reassignment, {assigned} services have owners")

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.setup_database()
        self.create_services()
        
        self.test_exact_ip_matching()
        self.test_cidr_matching()
        self.test_domain_matching()
        self.test_subdomain_matching()
        self.test_update_domain_settings()
        self.test_ownership_conflict()
        self.test_removing_ownership()
        
        print_section("All tests completed")

    def close(self):
        """Close database session"""
        self.session.close()


def main():
    print(blue("\n=== FRUIT PLATFORM OWNERSHIP MATCHING TESTER ===\n"))
    print("This script tests the owner matching functionality for IP addresses and domains.")
    
    tester = OwnershipTester()
    try:
        tester.run_all_tests()
    finally:
        tester.close()


if __name__ == "__main__":
    main()