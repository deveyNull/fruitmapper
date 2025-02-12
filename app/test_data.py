# test_data.py
from datetime import datetime
from models import (
    Base, FruitType, Fruit, Service, Owner, OwnerIP, OwnerDomain
)
import models as models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create database engine
DATABASE_URL = "sqlite:///./fruit_platform.db"
engine = create_engine(DATABASE_URL)

# Create all tables
Base.metadata.create_all(engine)

# Create session
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()
def verify_mappings():
    db = SessionLocal()
    try:
        print("\nVerifying Fruit Type Inheritance:")
        services = db.query(Service).all()
        for service in services:
            print(f"\nService {service.ip}:{service.port}")
            if service.fruit:
                print(f"- Associated Fruit: {service.fruit.name}")
                if service.fruit_type:
                    print(f"- Inherited Fruit Type: {service.fruit_type.name}")
                else:
                    print("- No fruit type (inheritance failed)")
            else:
                print("- No associated fruit")

        print("\nVerifying Owner Mappings:")
        for service in services:
            print(f"\nService {service.ip}:{service.port}")
            if service.owner:
                print(f"- Mapped to Owner: {service.owner.name}")
                matched_by = []
                if service.ip in [ip.ip for ip in service.owner.owned_ips]:
                    matched_by.append('IP')
                if service.domain in [d.domain for d in service.owner.owned_domains]:
                    matched_by.append('Domain')
                print(f"- Matched by: {' and '.join(matched_by) if matched_by else 'Unknown'}")
            else:
                print("- No owner mapping")

        # Add additional verification
        print("\nDetailed Service Information:")
        for service in services:
            print(f"\nService: {service.ip}:{service.port}")
            print(f"Fruit ID: {service.fruit_id}")
            print(f"Fruit Type ID: {service.fruit_type_id}")
            if service.fruit:
                print(f"Fruit: {service.fruit.name} (Type ID: {service.fruit.fruit_type_id})")
            if service.fruit_type:
                print(f"Fruit Type: {service.fruit_type.name}")

        return "Verification completed"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error during verification: {str(e)}"
    finally:
        db.close()

def create_test_data():
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(Service).delete()
        db.query(Fruit).delete()
        db.query(FruitType).delete()
        db.query(OwnerIP).delete()
        db.query(OwnerDomain).delete()
        db.query(Owner).delete()
        db.commit()

        # Create fruit types
        citrus = FruitType(name="Citrus", description="Citrus fruits")
        berry = FruitType(name="Berry", description="Berry fruits")
        db.add_all([citrus, berry])
        db.commit()
        db.refresh(citrus)
        db.refresh(berry)

        # Create fruits
        orange = Fruit(
            name="Orange",
            country_of_origin="Spain",
            date_picked=datetime.utcnow(),
            fruit_type_id=citrus.id
        )
        lemon = Fruit(
            name="Lemon",
            country_of_origin="Italy",
            date_picked=datetime.utcnow(),
            fruit_type_id=citrus.id
        )
        strawberry = Fruit(
            name="Strawberry",
            country_of_origin="USA",
            date_picked=datetime.utcnow(),
            fruit_type_id=berry.id
        )
        db.add_all([orange, lemon, strawberry])
        db.commit()
        db.refresh(orange)
        db.refresh(lemon)
        db.refresh(strawberry)

        # Create owners with IPs and domains
        owner1 = Owner(
            name="Citrus Corp",
            description="Major citrus provider",
            contact_info="contact@citruscorp.com"
        )
        owner2 = Owner(
            name="Berry Farms",
            description="Berry specialist",
            contact_info="info@berryfarms.com"
        )
        db.add_all([owner1, owner2])
        db.commit()

        # Add IPs and domains for owners
        owner1_ips = [
            OwnerIP(owner_id=owner1.id, ip="192.168.1.1"),
            OwnerIP(owner_id=owner1.id, ip="192.168.1.2")
        ]
        owner1_domains = [
            OwnerDomain(owner_id=owner1.id, domain="citruscorp.com"),
            OwnerDomain(owner_id=owner1.id, domain="citrus-corp.net")
        ]

        owner2_ips = [
            OwnerIP(owner_id=owner2.id, ip="192.168.2.1"),
            OwnerIP(owner_id=owner2.id, ip="192.168.2.2")
        ]
        owner2_domains = [
            OwnerDomain(owner_id=owner2.id, domain="berryfarms.com"),
            OwnerDomain(owner_id=owner2.id, domain="berry-farms.net")
        ]

        db.add_all(owner1_ips + owner1_domains + owner2_ips + owner2_domains)
        db.commit()

        # When creating services, explicitly set both fruit_id and fruit_type_id
        services = [
            Service(
                ip="192.168.1.1",
                port=80,
                domain="citruscorp.com",
                fruit_id=orange.id,
                fruit_type_id=orange.fruit_type_id
            ),
            Service(
                ip="192.168.2.1",
                port=443,
                domain="berryfarms.com",
                fruit_id=strawberry.id,
                fruit_type_id=strawberry.fruit_type_id
            ),
            Service(
                ip="192.168.1.2",
                port=8080,
                domain="unknown.com",
                fruit_id=lemon.id,
                fruit_type_id=lemon.fruit_type_id
            ),
            Service(
                ip="192.168.3.1",
                port=8443,
                domain="berry-farms.net",
                fruit_id=strawberry.id,
                fruit_type_id=strawberry.fruit_type_id
            ),
            Service(
                ip="192.168.4.1",
                port=80,
                domain="unknown.com",
                fruit_id=orange.id,
                fruit_type_id=orange.fruit_type_id
            )
        ]
        db.add_all(services)
        db.commit()

        return "Test data created successfully"
    
    except Exception as e:
        db.rollback()
        print(f"Error creating test data: {str(e)}")
        import traceback
        traceback.print_exc()
        return str(e)
    finally:
        db.close()

if __name__ == "__main__":
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    
    print("Creating test data...")
    result = create_test_data()
    print(result)
    
    print("\nVerifying mappings...")
    result = verify_mappings()
    print(result)