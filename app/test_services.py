#!/usr/bin/env python3
"""
Test script for service discovery and fingerprinting functionality.

This script tests:
1. Adding new services with various fingerprint data
2. Automatic matching of services to fruits based on fingerprints
3. Updating existing services with new fingerprint data
4. Batch service discovery simulation
"""

import os
import sys
import random
import json
import ipaddress
from datetime import datetime
from sqlalchemy import create_engine, and_, or_, not_
from sqlalchemy.orm import sessionmaker
import re

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

# Import models
from models import Base, User, FruitType, Fruit, Owner, OwnerIP, OwnerDomain, Service
from test_owner import print_test_header, print_section, print_success, print_failure, print_info

# Database URL - using testing database
TEST_DB_URL = "sqlite:///./test_fruit_platform.db"

class ServiceFingerprinter:
    """Test class for service discovery and fingerprinting functionality."""
    
    def __init__(self, db_url=TEST_DB_URL):
        """Initialize with database connection."""
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        # Store references to fruits and fruit types
        self.fruits = {}
        self.fruit_types = {}
        self._load_fruits_and_types()
    
    def _load_fruits_and_types(self):
        """Load existing fruits and fruit types from database."""
        # Load fruit types
        for fruit_type in self.session.query(FruitType).all():
            self.fruit_types[fruit_type.name] = fruit_type
            
        # Load fruits
        for fruit in self.session.query(Fruit).all():
            self.fruits[fruit.name] = fruit
    
    def setup_fingerprinting_tests(self):
        """Ensure we have the necessary fruit types and fruits for testing."""
        print_section("Setting up fingerprinting tests")
        
        # Check if we need to create fruit types
        required_types = ["web-server", "database", "mail-server", "iot-device", "unknown"]
        for type_name in required_types:
            if type_name not in self.fruit_types:
                print_info(f"Creating fruit type: {type_name}")
                fruit_type = FruitType(
                    name=type_name,
                    description=f"{type_name.replace('-', ' ').title()} servers"
                )
                self.session.add(fruit_type)
                self.session.commit()
                self.fruit_types[type_name] = fruit_type
        
        fingerprints = [
            # Web servers
            {
                "name": "nginx",
                "type": "web-server",
                "match_type": "banner",
                "match_regex": "nginx/[0-9\\.]+"
            },
            {
                "name": "apache",
                "type": "web-server",
                "match_type": "banner", 
                "match_regex": "Apache/[0-9\\.]+"
            },
            {
                "name": "iis",
                "type": "web-server",
                "match_type": "banner",
                "match_regex": "Microsoft-IIS/[0-9\\.]+"
            },
            
            # Databases
            {
                "name": "mysql",
                "type": "database",
                "match_type": "banner",
                "match_regex": "MySQL server"
            },
            {
                "name": "postgresql",
                "type": "database",
                "match_type": "banner",
                "match_regex": "PostgreSQL"
            },
            
            # Mail servers
            {
                "name": "exchange",
                "type": "mail-server",
                "match_type": "banner",
                "match_regex": "Microsoft Exchange"
            },
            {
                "name": "postfix",
                "type": "mail-server",
                "match_type": "banner",
                "match_regex": "Postfix"
            },
            
            # IoT devices
            {
                "name": "router",
                "type": "iot-device",
                "match_type": "html",
                "match_regex": "<title>Router Configuration</title>"
            },
            {
                "name": "camera",
                "type": "iot-device",
                "match_type": "html",
                "match_regex": "<title>IP Camera</title>"
            },
            
            # HTML content matching
            {
                "name": "wordpress",
                "type": "web-server",
                "match_type": "html",
                "match_regex": "wp-content"
            },
            
            # HTTP header matching
            {
                "name": "cloudflare",
                "type": "web-server",
                "match_type": "http_header",
                "match_regex": "cloudflare"
            },
            
            # Always need an unknown type
            {
                "name": "unknown",
                "type": "unknown",
                "match_type": "unknown",
                "match_regex": "unknown"
            }
        ]
        
        # Create fruits if they don't exist
        for fingerprint in fingerprints:
            if fingerprint["name"] not in self.fruits:
                print_info(f"Creating fruit: {fingerprint['name']}")
                
                # Get the fruit type
                fruit_type = self.fruit_types.get(fingerprint["type"])
                if not fruit_type:
                    print_failure(f"Fruit type {fingerprint['type']} not found!")
                    continue
                
                # Create the fruit
                fruit = Fruit(
                    name=fingerprint["name"],
                    date_picked=datetime.utcnow(),
                    fruit_type_id=fruit_type.id,
                    match_type=fingerprint["match_type"],
                    match_regex=fingerprint["match_regex"]
                )
                self.session.add(fruit)
                self.session.commit()
                self.fruits[fingerprint["name"]] = fruit
        
        print_success("Fingerprinting test setup complete")
    
    def test_add_service_with_fingerprint(self):
        """Test adding a new service with fingerprint data."""
        print_test_header("Adding Services with Fingerprints")
        
        # Test cases mapping fingerprint data to expected fruit
        test_cases = [
            {
                "name": "Nginx Web Server",
                "ip": "192.168.1.100",
                "port": 80,
                "banner_data": "HTTP/1.1 200 OK\r\nServer: nginx/1.18.0\r\nDate: Mon, 01 Jan 2024 12:00:00 GMT\r\n",
                "expected_fruit": "nginx"
            },
            {
                "name": "Apache Web Server",
                "ip": "192.168.1.101",
                "port": 8080,
                "banner_data": "HTTP/1.1 200 OK\r\nServer: Apache/2.4.41 (Ubuntu)\r\nDate: Mon, 01 Jan 2024 12:00:00 GMT\r\n",
                "expected_fruit": "apache"
            },
            {
                "name": "MySQL Database",
                "ip": "192.168.1.102",
                "port": 3306,
                "banner_data": "5.7.32-0ubuntu0.18.04.1\x00\x00\x00\x00\x00\x00\x00MySQL server\x00",
                "expected_fruit": "mysql"
            },
            {
                "name": "WordPress Site",
                "ip": "192.168.1.103",
                "port": 80,
                "html_data": "<html><head><title>My Blog</title></head><body><div class='wp-content'>WordPress content</div></body></html>",
                "expected_fruit": "wordpress"
            },
            {
                "name": "IP Camera",
                "ip": "192.168.1.104",
                "port": 8000,
                "html_data": "<html><head><title>IP Camera</title></head><body>Camera feed</body></html>",
                "expected_fruit": "camera"
            }
        ]
        
        # Run each test case
        for case in test_cases:
            print_info(f"Testing {case['name']} ({case['ip']}:{case['port']})")
            
            # Create basic service
            service = Service(
                ip=case["ip"],
                port=case["port"],
                domain=f"test-{case['ip'].replace('.', '-')}.example.com",
                asn="AS12345",
                country="US"
            )
            
            # Add fingerprint data
            if "banner_data" in case:
                service.banner_data = case["banner_data"]
            
            if "html_data" in case:
                # Properly set the http_data as JSON
                service.http_data = json.dumps({"html": case["html_data"]})
            
            if "http_headers" in case:
                # Properly set the http_data as JSON
                if service.http_data:
                    # If http_data already exists, update it
                    try:
                        data = json.loads(service.http_data)
                        data["headers"] = case["http_headers"]
                        service.http_data = json.dumps(data)
                    except (json.JSONDecodeError, TypeError):
                        service.http_data = json.dumps({"headers": case["http_headers"]})
                else:
                    service.http_data = json.dumps({"headers": case["http_headers"]})
            
            # Print debug info
            print_info(f"  Banner: {service.banner_data[:50]}..." if service.banner_data else "  Banner: None")
            print_info(f"  HTTP Data: {service.http_data[:50]}..." if service.http_data else "  HTTP Data: None")
                    
            # Add to database
            self.session.add(service)
            self.session.commit()
            
            # Refresh from database to get assigned fruit
            self.session.refresh(service)
            
            # Check if the fruit was assigned correctly
            if service.fruit and service.fruit.name == case["expected_fruit"]:
                print_success(f"Service correctly identified as {service.fruit.name}")
            else:
                fruit_name = service.fruit.name if service.fruit else "None"
                print_failure(f"Service identification failed: expected {case['expected_fruit']}, got {fruit_name}")
                print_info(f"  Service fruit_id: {service.fruit_id}")
                print_info(f"  Check that the match_regex pattern is correct for {case['expected_fruit']}")
                
    def test_update_service_fingerprint(self):
        """Test updating an existing service with new fingerprint data."""
        print_test_header("Updating Service Fingerprints")
        
        # Create a service with no initial fingerprint
        service = Service(
            ip="192.168.2.100",
            port=80,
            domain="updatetest.example.com",
            asn="AS12345",
            country="US"
        )
        self.session.add(service)
        self.session.commit()
        self.session.refresh(service)
        
        # Verify no fruit assigned initially
        if service.fruit_id is None:
            print_success("Initial service has no fruit type as expected")
        else:
            print_failure(f"Initial service unexpectedly has fruit assigned: {service.fruit.name}")
        
        # Update with nginx fingerprint
        print_info("Updating service with nginx fingerprint")
        service.banner_data = "HTTP/1.1 200 OK\r\nServer: nginx/1.18.0\r\n"
        self.session.commit()
        self.session.refresh(service)
        
        # Check if nginx was assigned
        if service.fruit and service.fruit.name == "nginx":
            print_success(f"Service correctly updated to nginx")
        else:
            print_failure(f"Service fingerprint update failed: expected nginx, got {service.fruit.name if service.fruit else 'None'}")
        
        # Update with apache fingerprint
        print_info("Updating service with apache fingerprint")
        service.banner_data = "HTTP/1.1 200 OK\r\nServer: Apache/2.4.41\r\n"
        self.session.commit()
        self.session.refresh(service)
        
        # Check if apache was assigned
        if service.fruit and service.fruit.name == "apache":
            print_success(f"Service correctly updated to apache")
        else:
            print_failure(f"Service fingerprint update failed: expected apache, got {service.fruit.name if service.fruit else 'None'}")
    
    def test_batch_service_discovery(self):
        """Test batch service discovery and fingerprinting."""
        print_test_header("Batch Service Discovery")
        
        # Sample scan results - simulates data from a network scanner
        # Updated to ensure pattern matches with our simple regex patterns
        scan_results = [
            {
                "ip": "10.0.1.1",
                "port": 80,
                "banner": "HTTP/1.1 200 OK\r\nServer: nginx/1.20.1\r\n",  # Contains 'nginx'
                "html": "<html><body>Welcome to nginx!</body></html>"
            },
            {
                "ip": "10.0.1.2",
                "port": 443,
                "banner": "HTTP/1.1 200 OK\r\nServer: Apache/2.4.51\r\n",  # Contains 'Apache'
                "html": "<html><body>It works!</body></html>"
            },
            {
                "ip": "10.0.1.3",
                "port": 3306,
                "banner": "5.7.36-0ubuntu0.18.04.1\x00MySQL server"  # Contains 'MySQL server'
            },
            {
                "ip": "10.0.1.4",
                "port": 8080,
                "banner": "HTTP/1.1 200 OK\r\n",
                "html": "<html><head><title>Router Configuration</title></head><body>Login to router</body></html>"
            },
            {
                "ip": "10.0.1.5",
                "port": 25,
                "banner": "220 mail.example.com ESMTP Postfix"  # Contains 'Postfix'
            }
        ]
        
        # Process the scan results
        print_info(f"Processing {len(scan_results)} scan results")
        
        # Keep track of matches
        matches = {fruit.name: 0 for fruit in self.session.query(Fruit).all()}
        matches["unknown"] = 0
        
        for scan in scan_results:
            # Check if service already exists
            existing = self.session.query(Service).filter_by(
                ip=scan["ip"],
                port=scan["port"]
            ).first()
            
            if existing:
                # Update existing service
                service = existing
                if "banner" in scan:
                    service.banner_data = scan["banner"]
                
                if "html" in scan:
                    # Properly format the HTTP data as JSON string
                    if service.http_data:
                        try:
                            data = json.loads(service.http_data)
                            data["html"] = scan["html"]
                            service.http_data = json.dumps(data)
                        except (json.JSONDecodeError, TypeError):
                            service.http_data = json.dumps({"html": scan["html"]})
                    else:
                        service.http_data = json.dumps({"html": scan["html"]})
            else:
                # Create new service
                service = Service(
                    ip=scan["ip"],
                    port=scan["port"],
                    asn="AS12345",
                    country="US"
                )
                
                if "banner" in scan:
                    service.banner_data = scan["banner"]
                
                if "html" in scan:
                    service.http_data = json.dumps({"html": scan["html"]})
                
                self.session.add(service)
            
            # Print debug info before commit
            print_info(f"Service {scan['ip']}:{scan['port']} data:")
            print_info(f"  Banner: {service.banner_data[:50]}..." if service.banner_data else "  Banner: None")
            print_info(f"  HTTP data: {service.http_data[:50]}..." if service.http_data else "  HTTP data: None")
                
            # Commit changes to trigger the fingerprinting event listeners
            self.session.commit()
            self.session.refresh(service)
            
            # Track the match
            if service.fruit:
                matches[service.fruit.name] += 1
                print_info(f"Service {scan['ip']}:{scan['port']} identified as {service.fruit.name}")
            else:
                matches["unknown"] += 1
                print_info(f"Service {scan['ip']}:{scan['port']} not identified")
                
            # Debug info - print fruit IDs and patterns that should match
            if service.fruit and service.fruit.name == "unknown":
                print_info(f"  → Checking why service was identified as unknown:")
                if "banner" in scan:
                    all_fruits = self.session.query(Fruit).filter_by(match_type="banner").all()
                    print_info(f"  → Banner data: {scan['banner'][:50]}...")
                    for fruit in all_fruits:
                        print_info(f"  → Checking against {fruit.name} pattern: {fruit.match_regex}")
                        try:
                            if re.search(fruit.match_regex, scan["banner"]):
                                print_info(f"  → Should have matched {fruit.name}!")
                        except Exception as e:
                            print_info(f"  → Error in regex: {str(e)}")
                if "html" in scan:
                    all_fruits = self.session.query(Fruit).filter_by(match_type="html").all()
                    print_info(f"  → HTML data: {scan['html'][:50]}...")
                    for fruit in all_fruits:
                        print_info(f"  → Checking against {fruit.name} pattern: {fruit.match_regex}")
                        try:
                            if re.search(fruit.match_regex, scan["html"]):
                                print_info(f"  → Should have matched {fruit.name}!")
                        except Exception as e:
                            print_info(f"  → Error in regex: {str(e)}")
        
        # Report on matches
        print_info("\nFingerprinting results:")
        for fruit_name, count in matches.items():
            if count > 0:
                print_info(f"  - {fruit_name}: {count} services")
        
        # Check if we have matches for each expected type
        expected_matches = {
            "nginx": 1,
            "apache": 1,
            "mysql": 1,
            "router": 1,
            "postfix": 1
        }
        
        success = True
        for fruit_name, expected_count in expected_matches.items():
            if matches.get(fruit_name, 0) != expected_count:
                print_failure(f"Expected {expected_count} {fruit_name} services, but found {matches.get(fruit_name, 0)}")
                success = False
        
        if success:
            print_success("All services correctly identified")
    
    def test_custom_regex_patterns(self):
        """Test the ability to add new fingerprints with custom regex patterns."""
        print_test_header("Custom Regex Fingerprinting")
        
        # Create a new fruit type if needed
        if "security" not in self.fruit_types:
            security_type = FruitType(
                name="security",
                description="Security devices and software"
            )
            self.session.add(security_type)
            self.session.commit()
            self.fruit_types["security"] = security_type
        
        # Create a new fruit with custom regex
        firewall_name = "custom-firewall"
        if firewall_name not in self.fruits:
            firewall = Fruit(
                name=firewall_name,
                date_picked=datetime.utcnow(),
                fruit_type_id=self.fruit_types["security"].id,
                match_type="banner",
                match_regex="FirewallD v[0-9.]+"
            )
            self.session.add(firewall)
            self.session.commit()
            self.fruits[firewall_name] = firewall
            print_success(f"Created new fruit {firewall_name} with custom regex")
        
        # Test the new pattern
        service = Service(
            ip="192.168.3.100",
            port=8443,
            banner_data="FirewallD v1.2.3 Enterprise Edition",
            asn="AS12345",
            country="US"
        )
        self.session.add(service)
        self.session.commit()
        self.session.refresh(service)
        
        if service.fruit and service.fruit.name == firewall_name:
            print_success(f"Service correctly identified with custom regex as {firewall_name}")
        else:
            print_failure(f"Custom regex identification failed: expected {firewall_name}, got {service.fruit.name if service.fruit else 'None'}")
    
    def run_all_tests(self):
        """Run all fingerprinting tests."""
        self.setup_fingerprinting_tests()
        self.test_add_service_with_fingerprint()
        self.test_update_service_fingerprint()
        self.test_batch_service_discovery()
        self.test_custom_regex_patterns()
        
        print_section("All fingerprinting tests completed")
    
    def close(self):
        """Close the database session."""
        self.session.close()

def main():
    """Main entry point for the script."""
    print("\n=== SERVICE DISCOVERY AND FINGERPRINTING TESTS ===\n")
    
    tester = ServiceFingerprinter()
    try:
        tester.run_all_tests()
    finally:
        tester.close()

if __name__ == "__main__":
    main()