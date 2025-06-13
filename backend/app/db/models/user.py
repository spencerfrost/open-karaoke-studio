"""
User SQLAlchemy model.
"""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash, check_password_hash
from .base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    theme = Column(String, nullable=True)
    color = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False
    @validates("username")
    def validate_username(self, key, username):
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return username
