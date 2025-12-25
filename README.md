# ScooterBug ERPNext App

Custom ERPNext/Frappe application for ScooterBug mobility equipment rental management.

## Overview

This app provides custom doctypes specifically designed for managing mobility equipment rentals at theme parks and tourist destinations.

## Features

### Custom Doctypes

| Doctype | Purpose |
|---------|---------|
| **Equipment** | Track individual scooters, wheelchairs, strollers with serial numbers, GPS, battery status |
| **Equipment Booking** | Manage rental reservations with dates, delivery info, pricing |
| **Booking Item** | Line items for equipment and lockers per booking |
| **Locker** | Theme park lockers with size, location, availability |
| **Travel Agent** | Partner agents with commission rates and tier levels |
| **Check-In/Out Log** | Equipment handoff tracking with photos and condition |
| **Maintenance Task** | Equipment service and repair tracking |
| **ScooterBug Location** | Rental locations (Orlando, Las Vegas, Anaheim) |

### API Endpoints

- `/api/method/scooterbug_erpnext.api.booking.create_booking` - Create new booking
- `/api/method/scooterbug_erpnext.api.booking.get_available_equipment` - Check availability
- `/api/method/scooterbug_erpnext.api.checkinout.check_in` - Process equipment check-in
- `/api/method/scooterbug_erpnext.api.checkinout.check_out` - Process equipment check-out

## Installation

### On Frappe Cloud

1. Go to your Frappe Cloud dashboard
2. Navigate to your site → Apps
3. Click "Install App"
4. Enter this repository URL: `https://github.com/ryanwbookingzone/scooterbug_erpnext`
5. Click Install

### Manual Installation (Bench)

```bash
# Navigate to your bench directory
cd frappe-bench

# Get the app
bench get-app https://github.com/ryanwbookingzone/scooterbug_erpnext

# Install on your site
bench --site your-site.local install-app scooterbug_erpnext

# Run migrations
bench --site your-site.local migrate
```

## Configuration

After installation, the app will automatically create:
- Default locations (Orlando FL, Las Vegas NV, Anaheim CA)
- Equipment categories (ECV Scooter, Stroller, Wheelchair, Rollator)
- Default locker sizes (Small, Medium, Large, Jumbo)

## Equipment Fields

| Field | Type | Description |
|-------|------|-------------|
| equipment_id | Data | Unique identifier (auto-generated) |
| equipment_name | Data | Display name |
| equipment_type | Link | Type of equipment |
| serial_number | Data | Manufacturer serial number |
| status | Select | Available, Rented, Maintenance, Reserved |
| location | Link | Current location |
| gps_latitude | Float | GPS coordinates |
| gps_longitude | Float | GPS coordinates |
| battery_level | Percent | Current battery level (for EVCs) |
| condition | Select | Excellent, Good, Fair, Needs Repair |
| last_maintenance_date | Date | Last service date |
| next_maintenance_date | Date | Scheduled service date |

## Booking Fields

| Field | Type | Description |
|-------|------|-------------|
| booking_id | Data | Unique booking number |
| customer | Link | Customer doctype |
| location | Link | Rental location |
| start_date | Date | Rental start |
| end_date | Date | Rental end |
| delivery_address | Text | Hotel/resort address |
| delivery_time | Time | Scheduled delivery |
| pickup_time | Time | Scheduled pickup |
| status | Select | Draft, Confirmed, In Progress, Completed, Cancelled |
| damage_waiver | Check | $6/day protection |
| grand_total | Currency | Total amount |
| travel_agent | Link | Referring agent (optional) |

## License

MIT License

## Support

For support, contact: ryanw@bookingzone.com
