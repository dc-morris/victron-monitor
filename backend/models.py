from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Battery
    battery_soc = Column(Float, nullable=True)  # State of charge %
    battery_voltage = Column(Float, nullable=True)  # Volts
    battery_current = Column(Float, nullable=True)  # Amps
    battery_power = Column(Float, nullable=True)  # Watts
    battery_temperature = Column(Float, nullable=True)  # Celsius

    # Solar
    solar_power = Column(Float, nullable=True)  # Watts
    solar_voltage = Column(Float, nullable=True)  # Volts
    solar_current = Column(Float, nullable=True)  # Amps
    solar_yield_today = Column(Float, nullable=True)  # kWh

    # Consumption
    consumption_power = Column(Float, nullable=True)  # Watts

    # Temperature sensor
    temperature = Column(Float, nullable=True)  # Celsius
    humidity = Column(Float, nullable=True)  # %

    # Battery state
    battery_state = Column(String, nullable=True)  # charging/idle/discharging
