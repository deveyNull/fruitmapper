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
            
            # Changed from fruit_types to fruits
            # First get the fruit names from the pipe-delimited list
            fruit_names = row['fruits'].split('|')
            
            # Add fruits to recipe
            for fruit_name in fruit_names:
                fruit = session.query(Fruit).filter_by(name=fruit_name.strip()).first()
                if fruit:
                    recipe.fruits.append(fruit)
                else:
                    print(f"Warning: Fruit {fruit_name} not found")
            
            session.add(recipe)
    session.commit()

def init_db():    
    # Load new data
    load_fruit_types('./sample_data/fruit_types.csv')
    load_fruits('./sample_data/new_fruits.csv')
    load_recipes('./sample_data/recipes.csv')

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully!")