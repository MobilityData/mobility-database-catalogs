from setuptools import setup

setup(
    name="mobility-catalogs",
    version="0.0.0",
    description="The Mobility Catalogs Library.",
    install_requires=["gtfs_kit", "pandas"],
    packages=["mobility_catalogs"],
)
