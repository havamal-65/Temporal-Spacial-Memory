from setuptools import setup, find_packages

setup(
    name="temporal_spatial_db",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-rocksdb>=0.7.0",
        "numpy>=1.23.0",
        "scipy>=1.9.0",
        "rtree>=1.0.0",
        "sortedcontainers>=2.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "sphinx>=6.0.0",
        ],
        "benchmark": [
            "pytest-benchmark>=4.0.0",
            "memory-profiler>=0.60.0",
        ],
    },
    python_requires=">=3.10",
    description="A temporal-spatial knowledge database for efficient storage and retrieval of data with spatial and temporal dimensions",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/temporal-spatial-db",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
) 