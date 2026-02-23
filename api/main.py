from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
import shutil
from decimal import Decimal
from datetime import timedelta

import models, schemas, auth, database, anpr
from database import engine, get_db

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ViScan API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure media directory exists
MEDIA_DIR = "media"
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

@app.get("/")
def hello():
    return {"mgs" : "Hello"}


@app.post("/register", response_model=schemas.UserResponse)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user_in.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create user with plain-text password
    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        password=user_in.password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create profile
    profile = models.UserProfile(
        user_id=new_user.id,
        upi_id=user_in.upi_id,
        mobile_number=user_in.mobile_number,
        wallet_balance=Decimal('0.00'),
        is_staff=False
    )
    db.add(profile)
    
    # Create initial vehicle if provided
    if user_in.vehicle_number:
        new_vehicle = models.Vehicle(
            user_id=new_user.id,
            plate_number=user_in.vehicle_number
        )
        db.add(new_vehicle)
    
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.Token)
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == login_data.username).first()
    if not user or login_data.password != user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/user_dashboard")
def get_user_dashboard(current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    vehicles = current_user.vehicles
    # Get violations for all user's vehicles
    vehicle_ids = [v.id for v in vehicles]
    violations = db.query(models.Violation).filter(models.Violation.vehicle_id.in_(vehicle_ids)).order_by(models.Violation.created.desc()).limit(50).all()
    
    return {
        "user": {
            "username": current_user.username,
            "email": current_user.email,
            "wallet_balance": current_user.profile.wallet_balance if current_user.profile else Decimal('0.00')
        },
        "vehicles": vehicles,
        "violations": violations
    }

@app.post("/add_vehicle", response_model=schemas.VehicleResponse)
def add_vehicle(vehicle_in: schemas.VehicleCreate, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    db_vehicle = db.query(models.Vehicle).filter(models.Vehicle.plate_number == vehicle_in.plate_number).first()
    if db_vehicle:
        raise HTTPException(status_code=400, detail="Vehicle already registered")
    
    new_vehicle = models.Vehicle(
        user_id=current_user.id,
        plate_number=vehicle_in.plate_number
    )
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle

@app.post("/add_money")
def add_money(deposit: schemas.WalletDeposit, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    if not current_user.profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    current_user.profile.wallet_balance += deposit.amount
    db.commit()
    return {"message": "Money added successfully", "new_balance": current_user.profile.wallet_balance}

@app.post("/detect")
async def detect_violation(image: UploadFile = File(...), db: Session = Depends(get_db)):
    # Save image
    filename = f"{uuid.uuid4().hex}_{image.filename}"
    file_path = os.path.join(MEDIA_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    # Extract plate
    plate_raw = anpr.extract_plate(file_path)
    if not plate_raw:
        raise HTTPException(status_code=400, detail="Plate not found")
    
    # Normalize plate (like in Django)
    plate_norm = plate_raw.upper().replace(" ", "").replace("-", "").strip()
    
    # Find matching vehicle
    # In SQLite, we might need to iterate or use a flexible query if stored values aren't normalized
    # For now, let's assume we match against stored plate_number after normalizing both
    all_vehicles = db.query(models.Vehicle).all()
    matching_vehicle = None
    for v in all_vehicles:
        if v.plate_number.upper().replace(" ", "").replace("-", "").strip() == plate_norm:
            matching_vehicle = v
            break
    
    if not matching_vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle not registered {plate_raw}")

    amount = Decimal('500.00')
    violation = models.Violation(
        vehicle_id=matching_vehicle.id,
        image=f"/media/{filename}",
        amount=amount,
        status="pending"
    )
    db.add(violation)
    db.flush() # Get violation ID

    # Automatic deduction logic
    user = matching_vehicle.user
    if user and user.profile:
        profile = user.profile
        if profile.wallet_balance >= amount:
            profile.wallet_balance -= amount
            violation.status = "paid"
            db.commit()
            return {"message": "Violation recorded and wallet debited", "plate": plate_raw}
        else:
            db.commit()
            return {"message": "Violation recorded — insufficient wallet balance, payment pending", "plate": plate_raw}
    
    db.commit()
    return {"message": "Violation recorded", "plate": plate_raw}

@app.post("/pay_violation/{violation_id}")
def pay_violation(violation_id: int, current_user: models.User = Depends(auth.get_current_active_user), db: Session = Depends(get_db)):
    violation = db.query(models.Violation).filter(models.Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    # Check ownership
    if violation.vehicle.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay this violation")
    
    if violation.status == "paid":
        return {"message": "Violation already paid"}
    
    profile = current_user.profile
    if profile.wallet_balance < violation.amount:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    profile.wallet_balance -= violation.amount
    violation.status = "paid"
    db.commit()
    return {"message": "Violation paid successfully"}

# Admin Endpoints
@app.get("/admin_dashboard")
def get_admin_dashboard(current_admin: models.User = Depends(auth.get_current_admin_user), db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    vehicles = db.query(models.Vehicle).all()
    violations = db.query(models.Violation).order_by(models.Violation.created.desc()).limit(500).all()
    
    return {
        "users_count": len(users),
        "vehicles_count": len(vehicles),
        "violations": violations,
        "users": users
    }

@app.post("/admin/vehicle", response_model=schemas.VehicleResponse)
def admin_add_vehicle(vehicle_in: schemas.AdminVehicleCreate, current_admin: models.User = Depends(auth.get_current_admin_user), db: Session = Depends(get_db)):
    db_vehicle = db.query(models.Vehicle).filter(models.Vehicle.plate_number == vehicle_in.plate_number).first()
    if db_vehicle:
        raise HTTPException(status_code=400, detail="Plate already exists")
    
    new_vehicle = models.Vehicle(
        plate_number=vehicle_in.plate_number,
        user_id=vehicle_in.owner_id
    )
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle

@app.put("/admin/vehicle/{vehicle_id}", response_model=schemas.VehicleResponse)
def admin_edit_vehicle(vehicle_id: int, vehicle_in: schemas.AdminVehicleUpdate, current_admin: models.User = Depends(auth.get_current_admin_user), db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Check if plate taken by another vehicle
    existing = db.query(models.Vehicle).filter(models.Vehicle.plate_number == vehicle_in.plate_number, models.Vehicle.id != vehicle_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plate already exists")
    
    vehicle.plate_number = vehicle_in.plate_number
    if vehicle_in.owner_id:
        vehicle.user_id = vehicle_in.owner_id
    
    db.commit()
    db.refresh(vehicle)
    return vehicle

@app.delete("/admin/vehicle/{vehicle_id}")
def admin_delete_vehicle(vehicle_id: int, current_admin: models.User = Depends(auth.get_current_admin_user), db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    db.delete(vehicle)
    db.commit()
    return {"message": "Vehicle deleted successfully"}
