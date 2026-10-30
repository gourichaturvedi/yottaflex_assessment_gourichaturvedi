from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass

class AddressZone(Base):
    __tablename__="address_zones"
    address_zone_id: Mapped[str]=mapped_column(String,primary_key=True); zone_name: Mapped[str]=mapped_column(String,unique=True); center_x_km: Mapped[float]=mapped_column(Float); center_y_km: Mapped[float]=mapped_column(Float); status: Mapped[str]=mapped_column(String,default="ACTIVE")
class ServiceDate(Base):
    __tablename__="service_dates"
    service_date: Mapped[str]=mapped_column(String,primary_key=True); day_number: Mapped[int]=mapped_column(Integer,unique=True); is_school_day: Mapped[bool]=mapped_column(Boolean,default=True); calendar_name: Mapped[str]=mapped_column(String,default="SYNTHETIC_200_DAY")
class Student(Base):
    __tablename__="students"
    student_id: Mapped[str]=mapped_column(String,primary_key=True); first_name: Mapped[str]=mapped_column(String); last_name: Mapped[str]=mapped_column(String); grade: Mapped[int]=mapped_column(Integer); address_line: Mapped[str]=mapped_column(String); address_zone_id: Mapped[str]=mapped_column(ForeignKey("address_zones.address_zone_id"),index=True); x_km: Mapped[float]=mapped_column(Float); y_km: Mapped[float]=mapped_column(Float); accessibility_required: Mapped[bool]=mapped_column(Boolean); pickup_window_start: Mapped[str]=mapped_column(String); pickup_window_end: Mapped[str]=mapped_column(String); address_approved: Mapped[bool]=mapped_column(Boolean); status: Mapped[str]=mapped_column(String); created_at: Mapped[str]=mapped_column(String)
    __table_args__=(CheckConstraint("grade BETWEEN 1 AND 12"),)
class GuardianContact(Base):
    __tablename__="guardian_contacts"
    guardian_contact_id: Mapped[str]=mapped_column(String,primary_key=True); student_id: Mapped[str]=mapped_column(ForeignKey("students.student_id"),index=True); relationship: Mapped[str]=mapped_column(String); synthetic_email: Mapped[str]=mapped_column(String,nullable=True); synthetic_phone: Mapped[str]=mapped_column(String,nullable=True); preferred_channel: Mapped[str]=mapped_column(String); is_primary: Mapped[bool]=mapped_column(Boolean); is_verified: Mapped[bool]=mapped_column(Boolean); consent_to_notify: Mapped[bool]=mapped_column(Boolean); effective_from: Mapped[str]=mapped_column(String); effective_to: Mapped[str]=mapped_column(String,nullable=True); status: Mapped[str]=mapped_column(String)
class Stop(Base):
    __tablename__="stops"
    stop_id: Mapped[str]=mapped_column(String,primary_key=True); stop_name: Mapped[str]=mapped_column(String); address_zone_id: Mapped[str]=mapped_column(ForeignKey("address_zones.address_zone_id"),index=True); x_km: Mapped[float]=mapped_column(Float); y_km: Mapped[float]=mapped_column(Float); pickup_window_start: Mapped[str]=mapped_column(String); pickup_window_end: Mapped[str]=mapped_column(String); accessible: Mapped[bool]=mapped_column(Boolean); approved: Mapped[bool]=mapped_column(Boolean); status: Mapped[str]=mapped_column(String)
class Bus(Base):
    __tablename__="buses"
    bus_id: Mapped[str]=mapped_column(String,primary_key=True); capacity: Mapped[int]=mapped_column(Integer); accessible: Mapped[bool]=mapped_column(Boolean); status: Mapped[str]=mapped_column(String); __table_args__=(CheckConstraint("capacity > 0"),)
class Driver(Base):
    __tablename__="drivers"
    driver_id: Mapped[str]=mapped_column(String,primary_key=True); driver_name: Mapped[str]=mapped_column(String); active: Mapped[bool]=mapped_column(Boolean); duty_limit_minutes: Mapped[int]=mapped_column(Integer)
class Route(Base):
    __tablename__="routes"
    route_id: Mapped[str]=mapped_column(String,primary_key=True); route_name: Mapped[str]=mapped_column(String); bus_id: Mapped[str]=mapped_column(ForeignKey("buses.bus_id"),index=True); driver_id: Mapped[str]=mapped_column(ForeignKey("drivers.driver_id"),index=True); depot_x_km: Mapped[float]=mapped_column(Float); depot_y_km: Mapped[float]=mapped_column(Float); planned_start_time: Mapped[str]=mapped_column(String); max_duration_minutes: Mapped[int]=mapped_column(Integer); effective_from: Mapped[str]=mapped_column(String); effective_to: Mapped[str]=mapped_column(String,nullable=True); status: Mapped[str]=mapped_column(String)
class RouteStop(Base):
    __tablename__="route_stops"
    route_stop_id: Mapped[str]=mapped_column(String,primary_key=True); route_id: Mapped[str]=mapped_column(ForeignKey("routes.route_id",ondelete="CASCADE"),index=True); stop_id: Mapped[str]=mapped_column(ForeignKey("stops.stop_id"),index=True); sequence_no: Mapped[int]=mapped_column(Integer); planned_arrival_time: Mapped[str]=mapped_column(String); planned_departure_time: Mapped[str]=mapped_column(String); travel_minutes_from_previous: Mapped[int]=mapped_column(Integer); status: Mapped[str]=mapped_column(String); __table_args__=(UniqueConstraint("route_id","sequence_no"),UniqueConstraint("route_id","stop_id"),CheckConstraint("sequence_no > 0"),CheckConstraint("travel_minutes_from_previous >= 0"))
class Assignment(Base):
    __tablename__="assignments"
    assignment_id: Mapped[str]=mapped_column(String,primary_key=True); student_id: Mapped[str]=mapped_column(ForeignKey("students.student_id"),index=True); route_stop_id: Mapped[str]=mapped_column(ForeignKey("route_stops.route_stop_id"),index=True); assigned_at: Mapped[str]=mapped_column(String); effective_from: Mapped[str]=mapped_column(String); effective_to: Mapped[str]=mapped_column(String,nullable=True); status: Mapped[str]=mapped_column(String); decision_code: Mapped[str]=mapped_column(String); decision_reason: Mapped[str]=mapped_column(Text)
class AttendanceEvent(Base):
    __tablename__="attendance_events"
    attendance_event_id: Mapped[str]=mapped_column(String,primary_key=True); assignment_id: Mapped[str]=mapped_column(ForeignKey("assignments.assignment_id"),index=True); service_date: Mapped[str]=mapped_column(String,index=True); status: Mapped[str]=mapped_column(String); observed_at: Mapped[str]=mapped_column(String); source: Mapped[str]=mapped_column(String); reason_code: Mapped[str]=mapped_column(String); notes: Mapped[str|None]=mapped_column(Text,nullable=True); __table_args__=(UniqueConstraint("assignment_id","service_date"),)
class Notification(Base):
    __tablename__="notifications"
    notification_id: Mapped[str]=mapped_column(String,primary_key=True); attendance_event_id: Mapped[str]=mapped_column(ForeignKey("attendance_events.attendance_event_id"),index=True); guardian_contact_id: Mapped[str]=mapped_column(ForeignKey("guardian_contacts.guardian_contact_id"),index=True); channel: Mapped[str]=mapped_column(String); template_code: Mapped[str]=mapped_column(String); status: Mapped[str]=mapped_column(String); created_at: Mapped[str]=mapped_column(String); sent_at: Mapped[str|None]=mapped_column(String,nullable=True); idempotency_key: Mapped[str]=mapped_column(String,unique=True); reason_code: Mapped[str|None]=mapped_column(String,nullable=True)
class BusCapacityEvent(Base):
    __tablename__="bus_capacity_events"
    capacity_event_id: Mapped[str]=mapped_column(String,primary_key=True); bus_id: Mapped[str]=mapped_column(ForeignKey("buses.bus_id"),index=True); effective_from: Mapped[str]=mapped_column(String); capacity_before: Mapped[int]=mapped_column(Integer); capacity_after: Mapped[int]=mapped_column(Integer); reason_code: Mapped[str]=mapped_column(String); created_at: Mapped[str]=mapped_column(String); __table_args__=(CheckConstraint("capacity_before > 0 AND capacity_after > 0"),)
class RouteDisruptionEvent(Base):
    __tablename__="route_disruption_events"
    disruption_event_id: Mapped[str]=mapped_column(String,primary_key=True); route_id: Mapped[str]=mapped_column(ForeignKey("routes.route_id"),index=True); service_date: Mapped[str]=mapped_column(String,index=True); affected_stop_id: Mapped[str|None]=mapped_column(ForeignKey("stops.stop_id"),nullable=True); disruption_type: Mapped[str]=mapped_column(String); delay_minutes: Mapped[int]=mapped_column(Integer); status: Mapped[str]=mapped_column(String); resolution_note: Mapped[str|None]=mapped_column(Text,nullable=True); created_at: Mapped[str]=mapped_column(String); __table_args__=(CheckConstraint("delay_minutes >= 0"),)
class AuditEvent(Base):
    __tablename__="audit_events"
    audit_event_id: Mapped[str]=mapped_column(String,primary_key=True); entity_type: Mapped[str]=mapped_column(String,index=True); entity_id: Mapped[str]=mapped_column(String,index=True); action: Mapped[str]=mapped_column(String); actor_role: Mapped[str]=mapped_column(String); occurred_at: Mapped[str]=mapped_column(String); reason: Mapped[str]=mapped_column(Text); before_json: Mapped[str|None]=mapped_column(Text,nullable=True); after_json: Mapped[str|None]=mapped_column(Text,nullable=True)

ALL_MODELS=[AddressZone,ServiceDate,Student,GuardianContact,Stop,Bus,Driver,Route,RouteStop,Assignment,AttendanceEvent,Notification,BusCapacityEvent,RouteDisruptionEvent,AuditEvent]
