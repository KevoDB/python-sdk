#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kevo",
    version="0.1.0",
    author="Kevo Team",
    author_email="info@example.com",
    description="Python SDK for Kevo key-value store",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jeremytregunna/kevo",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
    ],
    python_requires=">=3.8",
    install_requires=[
        "grpcio>=1.59.0",
        "grpcio-tools>=1.59.0",
        "protobuf>=4.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.5.1",
            "pylint>=2.17.5",
            "grpc-stubs>=1.53.0",
        ],
    },
)