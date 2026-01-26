"""SQLAlchemy models for Time Tracker."""
from . import db


class TimeBlock(db.Model):
    """Individual time block within a time entry."""
    __tablename__ = 'time_blocks'
    
    id = db.Column(db.Integer, primary_key=True)
    time_entry_id = db.Column(
        db.Integer, 
        db.ForeignKey('time_entries.id', ondelete='CASCADE'), 
        nullable=False
    )
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    def duration_hours(self) -> float:
        """Calculate duration in hours.
        
        Returns the difference between end_time and start_time in hours.
        """
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return (end_minutes - start_minutes) / 60.0


class ResearchGroup(db.Model):
    """Research group model for organizing time entries."""
    __tablename__ = 'research_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manager_name = db.Column(db.String(100), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    entries = db.relationship('TimeEntry', backref='group', lazy=True, cascade='all, delete-orphan')
    
    def get_total_hours(self):
        """Calculate total hours across all entries."""
        return sum(entry.total_hours for entry in self.entries)
    
    def get_total_pay(self, rate=107.93):
        """Calculate total pay based on hours and rate."""
        return round(self.get_total_hours() * rate, 2)


class TimeEntry(db.Model):
    """Time entry model for tracking work hours."""
    __tablename__ = 'time_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    research_group_id = db.Column(db.Integer, db.ForeignKey('research_groups.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    task_description = db.Column(db.String(500), nullable=False)
    total_hours = db.Column(db.Float, nullable=False, default=0.0)
    
    # Relationship to time blocks with cascade delete
    time_blocks = db.relationship(
        'TimeBlock', 
        backref='entry', 
        lazy=True,
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    
    def calculate_total_hours(self) -> float:
        """Calculate total hours from all time blocks.
        
        Returns the sum of all block durations, rounded to 2 decimal places.
        """
        total = sum(block.duration_hours() for block in self.time_blocks)
        return round(total, 2)
    
    def get_sorted_time_blocks(self):
        """Return time blocks sorted by start_time in chronological order."""
        return sorted(self.time_blocks, key=lambda block: block.start_time)
