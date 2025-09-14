# Import SQLAlchemy components for database modeling
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, ForeignKey, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

# Create base class for all database models
Base = declarative_base()

class Vendor(Base):
    """Vendor model storing company information and business details."""
    __tablename__ = 'vendors'

    # Primary key and core identification fields
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)  # Canonical company name
    nicknames = Column(Text)  # Alternative names, comma-separated
    domain = Column(String(255))  # Company website domain

    # Business information fields
    default_description = Column(Text)  # What the company does
    invoicing_country = Column(String(2))  # 2-letter ISO country code
    default_currency = Column(String(3))  # 3-letter ISO currency code
    default_product_type = Column(String(20))  # 'services' or 'goods'

    # Timestamp tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to transactions
    transactions = relationship("Transaction", back_populates="vendor")

class Transaction(Base):
    """Transaction model storing bank transaction data and AI analysis results."""
    __tablename__ = 'transactions'

    # Primary key and core transaction fields from CSV
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)  # Transaction date
    posting_date = Column(DateTime)  # Bank posting date
    text = Column(Text)  # Transaction description
    message = Column(Text)  # Additional message
    transaction_type = Column(String(50))  # Type from bank
    card_info = Column(String(50))  # Card number if applicable
    amount = Column(Float)  # Transaction amount
    currency = Column(String(3))  # Currency code
    sender = Column(Text)  # Sender information
    receiver = Column(Text)  # Receiver information
    note = Column(Text)  # Additional notes
    balance = Column(Float)  # Account balance after transaction

    # AI categorization results
    category = Column(String(100))  # AI-determined category
    category_confidence = Column(Float)  # Confidence in categorization

    # Vendor identification results
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    vendor = relationship("Vendor", back_populates="transactions")
    vendor_confidence = Column(Float)  # Confidence in vendor matching
    vendor_match_source = Column(String(20))  # How vendor was matched: 'cache', 'database', 'llm', or 'none'

    # Audit fields
    raw_line = Column(Text)  # Original CSV row data
    created_at = Column(DateTime, default=datetime.utcnow)
    batch_id = Column(String(36))  # UUID of processing batch for tracking latest processing

class VendorEnrichment(Base):
    """Track vendor data enrichment from various sources for audit purposes."""
    __tablename__ = 'vendor_enrichments'

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))  # Link to vendor
    enrichment_source = Column(String(50))  # Source of enrichment (AI, manual, etc.)
    enrichment_data = Column(Text)  # JSON data from enrichment source
    confidence = Column(Float)  # Confidence in enrichment accuracy
    created_at = Column(DateTime, default=datetime.utcnow)  # When enrichment occurred

def migrate_database():
    """Add missing columns to existing database."""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bank_transactions.db')

    if not os.path.exists(db_path):
        return  # No existing database to migrate

    engine = create_engine(f'sqlite:///{db_path}', echo=False)

    # Check if columns exist and add them if they don't
    with engine.connect() as conn:
        try:
            # Check if vendor_match_source column exists
            conn.execute(text("SELECT vendor_match_source FROM transactions LIMIT 1"))
        except Exception:
            # Column doesn't exist, add it
            conn.execute(text("ALTER TABLE transactions ADD COLUMN vendor_match_source VARCHAR(20)"))
            conn.commit()
            print("Added vendor_match_source column")

        try:
            # Check if batch_id column exists
            conn.execute(text("SELECT batch_id FROM transactions LIMIT 1"))
        except Exception:
            # Column doesn't exist, add it
            conn.execute(text("ALTER TABLE transactions ADD COLUMN batch_id VARCHAR(36)"))
            conn.commit()
            print("Added batch_id column")

def get_db_session():
    """Create and return configured SQLite database session."""
    # Define database file path relative to project structure
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bank_transactions.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Create SQLite engine and initialize all tables
    engine = create_engine(f'sqlite:///{db_path}', echo=False)

    # Run migration for existing databases
    migrate_database()

    # Create all tables (this will create new ones but not modify existing)
    Base.metadata.create_all(engine)

    # Return configured session for database operations
    Session = sessionmaker(bind=engine)
    return Session()