"""
Setup script for 5D Optical Storage Object Store.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="5d-optical-storage-object-store",
    version="1.0.0",
    author="Aionix Data",
    author_email="contact@aionix.com",
    description="Object store abstraction for 5D optical storage systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dssaurav2/5D-Optical-Storage-Device-by-Aionix-Data",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Filesystems",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.7",
    install_requires=[
        # No required dependencies - works with standard library
    ],
    extras_require={
        "s3": ["boto3>=1.26.0"],
        "dev": ["pytest>=7.0.0", "pytest-cov>=4.0.0"],
    },
    entry_points={
        "console_scripts": [
            "object-store-demo=example:main",
        ],
    },
)