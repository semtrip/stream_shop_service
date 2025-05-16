from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import DateTime
from db import Base

class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True)
    ip = Column(String)
    port = Column(Integer)
    type = Column(String)  # 'http', 'socks4', 'socks5'
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    twitchValid = Column(Boolean, default=False)
    youtubeValid = Column(Boolean, default=False)
    kickValid = Column(Boolean, default=False)

    useds = Column(Integer, default=0)


    active_accounts_count = Column(Integer, default=0)

    accounts = relationship("Account", back_populates="proxy")
    lastChecked = Column(DateTime, default=datetime.now())

