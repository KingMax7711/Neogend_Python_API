from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date
from database import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Real Information
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String, index=True)
    temp_password = Column(Boolean, default=True, nullable=False, server_default="true") # Force user to change password on first login
    discord_id = Column(String, index=True, nullable=True)
    inscription_date = Column(Date, index=True, nullable=True)
    inscription_status = Column(String, index=True, nullable=True)  # valid / pending / denied

    # RP Information
    rp_first_name = Column(String, index=True, nullable=True)
    rp_last_name = Column(String, index=True, nullable=True)
    rp_birthdate = Column(Date, index=True, nullable=True)
    rp_gender = Column(String, index=True, nullable=True)
    rp_grade = Column(String, index=True, nullable=True)
    rp_affectation = Column(String, index=True, nullable=True)
    rp_qualif = Column(String, index=True, nullable=True)
    rp_nipol = Column(String, index=True, nullable=False, unique=True)
    rp_server = Column(String, index=True, nullable=True)
    rp_service = Column(String, index=True, nullable=True) # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)

    # Admin
    privileges = Column(String, index=True, nullable=True) # Staff / Admin / Owner
    # Version des refresh tokens : incrémentée pour invalider tous les anciens
    token_version = Column(Integer, default=0, nullable=False, server_default="0")
