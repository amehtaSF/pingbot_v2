import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Interval

from app import db, create_app

load_dotenv()

# ------------------------------------------------
# Enrollments Table
# ------------------------------------------------
class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    telegram_id = db.Column(db.String(100), nullable=True, unique=False)
    telegram_link_code = db.Column(db.String(255), nullable=True)
    telegram_link_code_expire_ts = db.Column(db.DateTime(timezone=True), nullable=True)
    telegram_link_code_used = db.Column(db.Boolean, default=False, nullable=False)
    
    tz = db.Column(db.String(50), nullable=False)
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'), nullable=False)
    study_pid = db.Column(db.String(255), nullable=False)  # Participant ID in the study assigned by researcher
    enrolled = db.Column(db.Boolean, default=True, nullable=False)
    start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    pr_completed = db.Column(db.Float, default=0.0)
    
    dashboard_otp = db.Column(db.String(255), nullable=True)
    dashboard_otp_expire_ts = db.Column(db.DateTime(timezone=True), nullable=True)
    dashboard_otp_used = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    pings = db.relationship("Ping", back_populates="enrollment")
    study = db.relationship("Study", back_populates="enrollments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'telegram_link_code': self.telegram_link_code,
            'telegram_link_code_expire_ts': self.telegram_link_code_expire_ts.isoformat() if self.telegram_link_code_expire_ts else None,
            'telegram_link_code_used': self.telegram_link_code_used,
            'tz': self.tz,
            'study_id': self.study_id,
            'study_pid': self.study_pid,
            'enrolled': self.enrolled,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'pr_completed': self.pr_completed,
            'dashboard_otp': self.dashboard_otp,
            'dashboard_otp_expire_ts': self.dashboard_otp_expire_ts.isoformat() if self.dashboard_otp_expire_ts else None,
            'dashboard_otp_used': self.dashboard_otp_used,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    

# ------------------------------------------------
# UserStudy Table (Users ↔ Studies with attributes)
# ------------------------------------------------
class UserStudy(db.Model):
    __tablename__ = 'user_studies'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'), nullable=False)
    role = db.Column(db.String(255), nullable=False)  # e.g. 'owner': sharing + editing + viewing, 'editor': editing + viewing, 'viewer': viewing only
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="user_studies")
    study = db.relationship("Study", back_populates="user_studies")
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'study_id': self.study_id,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

# ------------------------------------------------
# Users Table
# ------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    institution = db.Column(db.String(255))
    prolific_token = db.Column(db.String(255))
    last_login = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Many-to-many relationship with Study
    user_studies = db.relationship(
        "UserStudy",
        back_populates="user"
    )

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password = generate_password_hash(password)
        
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'institution': self.institution,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

# ------------------------------------------------
# Studies Table
# ------------------------------------------------
class Study(db.Model):
    __tablename__ = 'studies'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_name = db.Column(db.String(255), nullable=False)
    internal_name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(255), nullable=False, unique=True)
    contact_message = db.Column(db.Text)  # e.g., "Please contact the study team for any questions or concerns by emailing ashm@stanford.edu."
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    ping_templates = db.relationship("PingTemplate", back_populates="study")
    pings = db.relationship("Ping", back_populates="study")
    enrollments = db.relationship(
        "Enrollment",
        back_populates="study"
    )
    user_studies = db.relationship(
        "UserStudy",
        back_populates="study"
    ) 
    
    def to_dict(self):
        return {
            'id': self.id,
            'public_name': self.public_name,
            'internal_name': self.internal_name,
            'code': self.code,
            'contact_message': self.contact_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
# ------------------------------------------------
# PingTemplates Table
# ------------------------------------------------
class PingTemplate(db.Model):
    __tablename__ = 'ping_templates'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(255))  # e.g., "https://qualtrics.com/survey"
    url_text = db.Column(db.String(255))  # e.g., "Click here to take the survey."
    reminder_latency = db.Column(Interval)  # e.g., '1 hour', '30 minutes'
    expire_latency = db.Column(Interval)    # e.g., '24 hours'
    schedule = db.Column(JSONB, nullable=True)  # e.g.,  [{"start_day_num": 1, "start_time": "09:00", "end_day_num": 1, "end_time": "10:00"}, {"day_num": 2, "start_time": "09:00", "end_time": "10:00"}]
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    study = db.relationship("Study", back_populates="ping_templates")
    pings = db.relationship("Ping", back_populates="ping_template")
    
    def to_dict(self):
        return {
            'id': self.id,
            'study_id': self.study_id,
            'name': self.name,
            'message': self.message,
            'url': self.url,
            'url_text': self.url_text,
            'reminder_latency': str(self.reminder_latency),
            'expire_latency': str(self.expire_latency),
            'schedule': self.schedule,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

# ------------------------------------------------
# Pings Table
# ------------------------------------------------
class Ping(db.Model):
    __tablename__ = 'pings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    study_id = db.Column(db.Integer, db.ForeignKey('studies.id'), nullable=False)
    ping_template_id = db.Column(db.Integer, db.ForeignKey('ping_templates.id'), nullable=False)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=False)
    
    scheduled_ts = db.Column(db.DateTime(timezone=True), nullable=False)
    expire_ts = db.Column(db.DateTime(timezone=True))
    reminder_ts = db.Column(db.DateTime(timezone=True))
    ping_sent = db.Column(db.Boolean, nullable=False, default=False)
    reminder_sent = db.Column(db.Boolean, nullable=False, default=False)
    
    forwarding_code = db.Column(db.String(255), nullable=False, default=lambda: os.urandom(16).hex())
    
    day_num = db.Column(db.Integer, nullable=False)
    
    message = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    study = db.relationship("Study", back_populates="pings")
    ping_template = db.relationship("PingTemplate", back_populates="pings")
    enrollment = db.relationship("Enrollment", back_populates="pings")
    # participant = db.relationship("Participant", back_populates="pings")
    
    def to_dict(self):
        return {
            'id': self.id,
            'study_id': self.study_id,
            'ping_template_id': self.ping_template_id,
            'enrollment_id': self.enrollment_id,
            'scheduled_ts': self.scheduled_ts.isoformat() if self.scheduled_ts else None,
            'expire_ts': self.expire_ts.isoformat() if self.expire_ts else None,
            'reminder_ts': self.reminder_ts.isoformat() if self.reminder_ts else None,
            'day_num': self.day_num,
            'message': self.message,
            'url': self.url,
            'ping_sent': self.ping_sent,
            'reminder_sent': self.reminder_sent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
