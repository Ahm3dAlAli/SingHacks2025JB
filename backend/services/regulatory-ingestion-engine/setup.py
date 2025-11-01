from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="regulatory-ingestion-engine",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Regulatory Document Ingestion and Processing Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/regulatory-ingestion-engine",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "python-dotenv>=0.19.0",
        "sqlalchemy>=1.4.0",
        "alembic>=1.7.0",
        "psycopg2-binary>=2.9.0",
        "pydantic>=1.8.0",
        "python-multipart>=0.0.5",
        "PyMuPDF>=1.19.0",
        "python-docx>=0.8.11",
        "beautifulsoup4>=4.10.0",
        "lxml>=4.6.0",
        "spacy>=3.0.0",
        "loguru>=0.5.0",
        "requests>=2.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.15.0",
            "black>=21.0",
            "isort>=5.0.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
            "pre-commit>=2.15.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "regulatory-ingest=app.cli:main",
        ],
    },
)
