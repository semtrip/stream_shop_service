from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, nullable=True)
    token = Column(String, nullable=False)
    cookies = Column(String, nullable=False)

    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True)
    platform = Column(String, nullable=False)  # youtube, kick, twitch
    isValid = Column(Boolean, default=False, nullable=False)

    proxy = relationship("Proxy", back_populates="accounts")