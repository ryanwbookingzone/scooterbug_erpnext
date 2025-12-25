import frappe

def after_install():
    """Setup initial data after app installation"""
    create_locations()
    create_sample_equipment_types()
    print("ScooterBug app installed successfully!")

def create_locations():
    """Create default ScooterBug locations"""
    locations = [
        {
            "location_code": "ORLANDO",
            "location_name": "Orlando, FL",
            "city": "Orlando",
            "state": "FL",
            "timezone": "America/New_York",
            "phone": "1-800-726-8284",
            "email": "orlando@scooterbug.com",
            "operating_hours_start": "07:00:00",
            "operating_hours_end": "22:00:00",
            "delivery_radius_miles": 30,
            "base_delivery_fee": 0,
            "is_active": 1
        },
        {
            "location_code": "LASVEGAS",
            "location_name": "Las Vegas, NV",
            "city": "Las Vegas",
            "state": "NV",
            "timezone": "America/Los_Angeles",
            "phone": "1-800-726-8284",
            "email": "lasvegas@scooterbug.com",
            "operating_hours_start": "07:00:00",
            "operating_hours_end": "23:00:00",
            "delivery_radius_miles": 25,
            "base_delivery_fee": 0,
            "is_active": 1
        },
        {
            "location_code": "ANAHEIM",
            "location_name": "Anaheim, CA",
            "city": "Anaheim",
            "state": "CA",
            "timezone": "America/Los_Angeles",
            "phone": "1-800-726-8284",
            "email": "anaheim@scooterbug.com",
            "operating_hours_start": "07:00:00",
            "operating_hours_end": "22:00:00",
            "delivery_radius_miles": 20,
            "base_delivery_fee": 0,
            "is_active": 1
        }
    ]
    
    for loc in locations:
        if not frappe.db.exists("ScooterBug Location", loc["location_code"]):
            doc = frappe.get_doc({
                "doctype": "ScooterBug Location",
                **loc
            })
            doc.insert(ignore_permissions=True)
            print(f"Created location: {loc['location_name']}")

def create_sample_equipment_types():
    """Create sample equipment for demonstration"""
    equipment_list = [
        {
            "equipment_id": "EQ-0001",
            "equipment_name": "Pride Go-Go Elite Traveller",
            "equipment_type": "ECV Scooter",
            "category": "ECV Scooter",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "PGE-2024-0001",
            "manufacturer": "Pride Mobility",
            "model": "Go-Go Elite Traveller",
            "weight_lbs": 96,
            "weight_capacity_lbs": 325,
            "battery_life_hours": 8,
            "max_speed_mph": 4.5,
            "daily_rate": 55,
            "weekly_rate": 275,
            "damage_waiver_rate": 6,
            "current_battery_level": 100,
            "is_available": 1,
            "features": "Adjustable tiller, Front basket, USB charging port, LED headlight"
        },
        {
            "equipment_id": "EQ-0002",
            "equipment_name": "Drive Medical Scout",
            "equipment_type": "Standard Scooter",
            "category": "ECV Scooter",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "DMS-2024-0001",
            "manufacturer": "Drive Medical",
            "model": "Scout",
            "weight_lbs": 85,
            "weight_capacity_lbs": 300,
            "battery_life_hours": 6,
            "max_speed_mph": 4,
            "daily_rate": 45,
            "weekly_rate": 225,
            "damage_waiver_rate": 6,
            "current_battery_level": 100,
            "is_available": 1,
            "features": "Compact design, Easy disassembly, Front basket"
        },
        {
            "equipment_id": "EQ-0003",
            "equipment_name": "Medline Standard Wheelchair",
            "equipment_type": "Standard Wheelchair",
            "category": "Wheelchair",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "MSW-2024-0001",
            "manufacturer": "Medline",
            "model": "Standard",
            "weight_lbs": 35,
            "weight_capacity_lbs": 300,
            "daily_rate": 15,
            "weekly_rate": 75,
            "damage_waiver_rate": 3,
            "is_available": 1,
            "features": "Folding frame, Swing-away footrests, Padded armrests"
        },
        {
            "equipment_id": "EQ-0004",
            "equipment_name": "Baby Jogger City Mini Double",
            "equipment_type": "Double Stroller",
            "category": "Stroller",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "BJD-2024-0001",
            "manufacturer": "Baby Jogger",
            "model": "City Mini Double",
            "weight_lbs": 26,
            "weight_capacity_lbs": 100,
            "daily_rate": 25,
            "weekly_rate": 125,
            "damage_waiver_rate": 4,
            "is_available": 1,
            "features": "Side-by-side seating, One-hand fold, UV canopy, Storage basket"
        }
    ]
    
    for eq in equipment_list:
        if not frappe.db.exists("Equipment", eq["equipment_id"]):
            doc = frappe.get_doc({
                "doctype": "Equipment",
                **eq
            })
            doc.insert(ignore_permissions=True)
            print(f"Created equipment: {eq['equipment_name']}")
    
    frappe.db.commit()
