import os
import csv
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, FruitType, Fruit, Recipe
from passlib.hash import bcrypt

# Create database engine
DATABASE_URL = "sqlite:///./fruit_platform.db"
engine = create_engine(DATABASE_URL)

# Create all tables
Base.metadata.create_all(engine)

# Create session
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def load_fruit_types(filename):
    """Load fruit types from CSV file"""
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fruit_type = FruitType(
                name=row['name'],
                description=row['description']
            )
            session.add(fruit_type)
    session.commit()

def load_fruits(filename):
    """Load fruits from CSV file"""
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Get fruit type
            fruit_type = session.query(FruitType).filter_by(name=row['fruit_type']).first()
            if not fruit_type:
                print(f"Warning: Fruit type {row['fruit_type']} not found")
                continue
            
            fruit = Fruit(
                name=row['name'],
                country_of_origin=row['country_of_origin'],
                date_picked=datetime.strptime(row['date_picked'], '%Y-%m-%d'),
                fruit_type_id=fruit_type.id
            )
            session.add(fruit)
    session.commit()

def load_recipes(filename):
    """Load recipes from CSV file"""
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            recipe = Recipe(
                name=row['name'],
                description=row['description'],
                instructions=row['instructions'],
                preparation_time=int(row['preparation_time'])
            )
            
            # Add fruit types to recipe
            fruit_types = row['fruit_types'].split('|')
            for ft_name in fruit_types:
                fruit_type = session.query(FruitType).filter_by(name=ft_name.strip()).first()
                if fruit_type:
                    recipe.fruit_types.append(fruit_type)
                else:
                    print(f"Warning: Fruit type {ft_name} not found")
            
            session.add(recipe)
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
    session.commit()

def init_db():
    """Initialize database with sample data"""
    # Create admin user
    create_admin_user()
    
    # Load sample data
    load_fruit_types('./sample_data/fruit_types.csv')
    load_fruits('./sample_data/fruits.csv')
    load_recipes('./sample_data/recipes.csv')

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")