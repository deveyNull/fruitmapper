# Fruit Platform
## Overview

Fruit Platform is a service management system that automatically categorizes and manages services based on pattern matching and ownership relationships. It provides automatic service-to-fruit matching based on configurable criteria and maintains owner relationships through IP and domain associations.
Features


## Quick Start

Clone the repository
Set up virtual environment:

python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

Install dependencies:

pip install -r requirements.txt

Set up environment:

cp .env.example .env
# Edit .env with your settings

Initialize database:

python init_db.py

Run the application:

uvicorn app.main:app --reload