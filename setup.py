from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="scooterbug_erpnext",
    version="1.0.0",
    description="ScooterBug Equipment Rental Management for ERPNext",
    author="BookingZone",
    author_email="ryanw@bookingzone.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
