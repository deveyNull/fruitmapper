# File: checkdb.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from models import FruitType, Fruit, Recipe, Owner, Service

# Get the absolute path to the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "fruit_platform.db")

# Create database connection
DATABASE_URL = f"sqlite:///{DB_PATH}"
print(f"Looking for database at: {DB_PATH}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_database():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at {DB_PATH}")
        return

    db = SessionLocal()
    try:
        print("\n=== Fruit Types ===")
        fruit_types = db.query(FruitType).all()
        if not fruit_types:
            print("No fruit types found in database!")
        for ft in fruit_types:
            print(f"\nFruit Type ID: {ft.id}")
            print(f"Name: {ft.name}")
            print(f"Description: {ft.description}")
            print(f"Number of fruits: {len(ft.fruits)}")
            print(f"Number of recipes: {len(ft.recipes)}")

        print("\n=== Fruits ===")
        fruits = db.query(Fruit).all()
        if not fruits:
            print("No fruits found in database!")
        for fruit in fruits:
            print(f"\nFruit ID: {fruit.id}")
            print(f"Name: {fruit.name}")
            print(f"Type: {fruit.fruit_type.name if fruit.fruit_type else 'No type assigned'}")
            print(f"Country of Origin: {fruit.country_of_origin}")
            print(f"Date Picked: {fruit.date_picked}")

        print("\n=== Recipes ===")
        recipes = db.query(Recipe).all()
        if not recipes:
            print("No recipes found in database!")
        for recipe in recipes:
            print(f"\nRecipe ID: {recipe.id}")
            print(f"Name: {recipe.name}")
            print(f"Description: {recipe.description}")
            print("Compatible Fruit Types:", ', '.join(ft.name for ft in recipe.fruit_types))
            print(f"Preparation Time: {recipe.preparation_time} minutes")
            print("Instructions:", recipe.instructions.replace('\n', '\n\t'))
        print("\n=== Owners ===")
        owners = db.query(Owner).all()
        if not owners:
            print("No owners found in database!")
        for owner in owners:
            print(f"\nRecipe ID: {owner.id}")
            print(f"Name: {owner.name}")
        print("\n===Services===")
        services = db.query(Service).all()
        if not services:
            print("No services found in database!")
        for service in services:
            print(f"\nService ID: {service.id}")
            print(f"IP:Port {service.ip} {service.port}")
            print(f"\nFruit ID: {fruit.id}")
            print(f"\nOwner ID: {owner.id}")




    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database()