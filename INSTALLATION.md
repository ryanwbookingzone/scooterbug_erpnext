# Installing ScooterBug ERPNext App on Frappe Cloud

## Step-by-Step Installation Guide

### Step 1: Access Frappe Cloud Dashboard

1. Go to [https://frappecloud.com](https://frappecloud.com)
2. Log in with your account (ryanw@bookingzone.com)
3. Navigate to your site: **bzone.v.erpnext.com**

### Step 2: Install the Custom App

1. Click on your site name to open site details
2. Go to the **Apps** tab
3. Click **"+ Add App"** or **"Install App"**
4. Select **"Add from GitHub"**
5. Enter the repository URL:
   ```
   https://github.com/ryanwbookingzone/scooterbug_erpnext
   ```
6. Select the **main** branch
7. Click **Install**

### Step 3: Wait for Installation

- Frappe Cloud will automatically:
  - Clone the repository
  - Install dependencies
  - Run migrations to create the custom doctypes
  - Restart your site

- This process typically takes 2-5 minutes

### Step 4: Verify Installation

1. Go to your ERPNext site: https://bzone.v.erpnext.com
2. Open the **Search Bar** (Ctrl+K or Cmd+K)
3. Search for "Equipment" - you should see the new doctype
4. Check the module list for "ScooterBug"

### Step 5: Initial Setup

After installation, go to:

1. **ScooterBug Location** - Add your rental locations:
   - Orlando, FL
   - Las Vegas, NV
   - Anaheim, CA

2. **Equipment** - Add your fleet:
   - ECV Scooters
   - Strollers
   - Wheelchairs
   - Rollators

3. **Locker** - Configure theme park lockers

4. **Travel Agent** - Add partner travel agents

## Custom Doctypes Created

| Doctype | Menu Location |
|---------|---------------|
| Equipment | ScooterBug → Equipment |
| Equipment Booking | ScooterBug → Equipment Booking |
| Booking Item | (Child table) |
| Locker | ScooterBug → Locker |
| Travel Agent | ScooterBug → Travel Agent |
| Check In Out Log | ScooterBug → Check In Out Log |
| Maintenance Task | ScooterBug → Maintenance Task |
| ScooterBug Location | ScooterBug → ScooterBug Location |

## Updating the Admin Panel

Once the custom doctypes are installed, update the admin panel to use them:

1. In the ScooterBug Booking Platform code, update `server/erpnext/service.ts`
2. Change doctype references from standard to custom:
   - `Item` → `Equipment`
   - `Sales Order` → `Equipment Booking`
   - `Customer` → `Travel Agent`
   - `Asset Maintenance Log` → `Maintenance Task`

## Troubleshooting

### App not appearing after installation

1. Clear browser cache
2. Run bench migrate manually (if you have bench access):
   ```bash
   bench --site bzone.v.erpnext.com migrate
   ```

### Permission errors

1. Go to **Role Permission Manager**
2. Add permissions for the new doctypes to appropriate roles

### API errors

1. Ensure your API key has access to the new doctypes
2. Check the Error Log in ERPNext for details

## Support

For issues with this app, contact: ryanw@bookingzone.com

Repository: https://github.com/ryanwbookingzone/scooterbug_erpnext
