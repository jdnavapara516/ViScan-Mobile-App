from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from decimal import Decimal

def seed_admin():
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if admin:
            print("Admin user already exists.")
            return

        # Create admin user
        # Note: Using plain text password as per current app login logic (see login endpoint in main.py)
        new_admin = models.User(
            username="admin",
            email="admin@viscan.com",
            password="admin",
            is_active=True
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)

        # Create admin profile
        profile = models.UserProfile(
            user_id=new_admin.id,
            upi_id="admin@upi",
            mobile_number="0000000000",
            wallet_balance=Decimal('10000.00'),
            is_staff=True
        )
        db.add(profile)
        db.commit()
        print("Admin user 'admin' with password 'admin' created successfully.")
    except Exception as e:
        print(f"Error seeding admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
