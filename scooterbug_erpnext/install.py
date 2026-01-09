import frappe

def after_install():
    """Setup initial data after app installation"""
    try:
        # Only create data if the doctypes exist
        if frappe.db.exists("DocType", "SB Location"):
            create_locations()
        else:
            print("SB Location doctype not found, skipping location creation")
        
        if frappe.db.exists("DocType", "SB Equipment Type"):
            create_equipment_types()
        else:
            print("SB Equipment Type doctype not found, skipping equipment type creation")
        
        if frappe.db.exists("DocType", "SB Equipment"):
            create_sample_equipment()
        else:
            print("SB Equipment doctype not found, skipping equipment creation")
        
        print("ScooterBug app installed successfully!")
    except Exception as e:
        print(f"Warning during ScooterBug installation: {e}")
        print("You may need to run bench migrate to create the doctypes first")

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
        try:
            if not frappe.db.exists("SB Location", loc["location_code"]):
                doc = frappe.get_doc({
                    "doctype": "SB Location",
                    **loc
                })
                doc.insert(ignore_permissions=True)
                print(f"Created location: {loc['location_name']}")
        except Exception as e:
            print(f"Could not create location {loc['location_name']}: {e}")

def create_equipment_types():
    """Create default equipment types"""
    equipment_types = [
        {
            "type_name": "ECV Scooter",
            "category": "Mobility",
            "description": "Electric Convenience Vehicle - 4-wheel scooter for mobility assistance",
            "daily_rate": 55,
            "weekly_rate": 275,
            "damage_waiver_rate": 6
        },
        {
            "type_name": "Standard Wheelchair",
            "category": "Mobility",
            "description": "Manual wheelchair for mobility assistance",
            "daily_rate": 15,
            "weekly_rate": 75,
            "damage_waiver_rate": 3
        },
        {
            "type_name": "Double Stroller",
            "category": "Stroller",
            "description": "Side-by-side double stroller for two children",
            "daily_rate": 25,
            "weekly_rate": 125,
            "damage_waiver_rate": 4
        },
        {
            "type_name": "Single Stroller",
            "category": "Stroller",
            "description": "Single stroller for one child",
            "daily_rate": 18,
            "weekly_rate": 90,
            "damage_waiver_rate": 3
        }
    ]
    
    for eq_type in equipment_types:
        try:
            if not frappe.db.exists("SB Equipment Type", eq_type["type_name"]):
                doc = frappe.get_doc({
                    "doctype": "SB Equipment Type",
                    **eq_type
                })
                doc.insert(ignore_permissions=True)
                print(f"Created equipment type: {eq_type['type_name']}")
        except Exception as e:
            print(f"Could not create equipment type {eq_type['type_name']}: {e}")

def create_sample_equipment():
    """Create sample equipment for demonstration"""
    equipment_list = [
        {
            "equipment_id": "EQ-0001",
            "equipment_type": "ECV Scooter",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "PGE-2024-0001",
            "manufacturer": "Pride Mobility",
            "model": "Go-Go Elite Traveller",
            "current_battery_level": 100
        },
        {
            "equipment_id": "EQ-0002",
            "equipment_type": "ECV Scooter",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "DMS-2024-0001",
            "manufacturer": "Drive Medical",
            "model": "Scout",
            "current_battery_level": 100
        },
        {
            "equipment_id": "EQ-0003",
            "equipment_type": "Standard Wheelchair",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "MSW-2024-0001",
            "manufacturer": "Medline",
            "model": "Standard"
        },
        {
            "equipment_id": "EQ-0004",
            "equipment_type": "Double Stroller",
            "location": "ORLANDO",
            "status": "Available",
            "serial_number": "BJD-2024-0001",
            "manufacturer": "Baby Jogger",
            "model": "City Mini Double"
        }
    ]
    
    for eq in equipment_list:
        try:
            if not frappe.db.exists("SB Equipment", eq["equipment_id"]):
                doc = frappe.get_doc({
                    "doctype": "SB Equipment",
                    **eq
                })
                doc.insert(ignore_permissions=True)
                print(f"Created equipment: {eq['equipment_id']}")
        except Exception as e:
            print(f"Could not create equipment {eq['equipment_id']}: {e}")
    
    try:
        frappe.db.commit()
    except Exception:
        pass
