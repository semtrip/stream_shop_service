from sqlalchemy import Column, Integer, String, Boolean, DateTime
from db import Base

class Proxy(Base):
    __tablename__ = "proxy"
    
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String)
    password = Column(String)
    type = Column(String, nullable=False)  # https, socks, socks5
    useds = Column(Integer, default=0)
    twitchValid = Column(Boolean, default=False, nullable=False)
    youtubeValid = Column(Boolean, default=False, nullable=False)
    kickValid = Column(Boolean, default=False, nullable=False)
    lastChecked = Column(DateTime, nullable=False)
