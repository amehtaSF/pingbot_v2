import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Interval

from app import db, create_app

load_dotenv()


def drop_tables():
    """
    Drops all tables in the database by invoking db.drop_all()
    within a Flask application context.
    """
    app = create_app()
    with app.app_context():
        try:
            db.drop_all()
            db.session.commit()
            print("All tables dropped successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error dropping tables: {e}")

def create_tables():
    """
    Creates all tables in the database by invoking db.create_all()
    within a Flask application context.
    """
    app = create_app()
    with app.app_context():
        try:
            db.create_all()
            db.session.commit()
            print("All tables created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating tables: {e}")

if __name__ == '__main__':
    # print("Dropping all tables...")
    # drop_tables()
    print("Creating all tables...")
    create_tables()
    

'''
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO ashish;
'''