from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector


Base = declarative_base()

class Document(Base):

    __tablename__ = 'documents'

    doc_id = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    report_year = Column(Integer)
    file_path = Column(String(255), nullable=False)
    processed_at = Column(DateTime, server_default=func.now())


    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    tables = relationship("ExtractedTable", back_populates="document", cascade="all, delete-orphan")
    images = relationship("ExtractedImage", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.doc_id}, name='{self.company_name} {self.report_year}')>"

class DocumentChunk(Base):

    __tablename__ = 'document_chunks'

    id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('documents.doc_id'), nullable=False)
    page_number = Column(Integer)
    chunk_text = Column(Text)
    embedding = Column(Vector(1536)) 


    document = relationship("Document", back_populates="chunks")

class ExtractedTable(Base):

    __tablename__ = 'extracted_tables'

    table_id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('documents.doc_id'), nullable=False)
    page_number = Column(Integer)
    table_data_json = Column(JSONB)
    table_as_text = Column(Text)
    embedding = Column(Vector(1536))

    document = relationship("Document", back_populates="tables")

class ExtractedImage(Base):

    __tablename__ = 'extracted_images'

    image_id = Column(Integer, primary_key=True)
    doc_id = Column(Integer, ForeignKey('documents.doc_id'), nullable=False)
    page_number = Column(Integer)
    image_filename = Column(String(255))
    image_path = Column(String(500))
    document = relationship("Document", back_populates="images")

