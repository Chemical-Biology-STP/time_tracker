"""REST API blueprint for Time Tracker companion app integration."""
from datetime import datetime, time
from flask import Blueprint, jsonify, request
from .models import db, ResearchGroup, TimeEntry, TimeBlock

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for connectivity testing."""
    return jsonify({'status': 'ok'})


@api_bp.route('/groups', methods=['GET'])
def get_groups():
    """Return all research groups as JSON array."""
    groups = ResearchGroup.query.all()
    return jsonify([{
        'id': g.id,
        'name': g.name,
        'manager_name': g.manager_name,
        'project_name': g.project_name
    } for g in groups])


@api_bp.route('/groups', methods=['POST'])
def create_group():
    """Create a new research group."""
    data = request.get_json()
    
    # Validate required fields
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    if not data.get('name'):
        return jsonify({'error': 'name required'}), 400
    
    # Create group with optional fields
    group = ResearchGroup(
        name=data['name'].strip(),
        manager_name=data.get('manager_name', '').strip(),
        project_name=data.get('project_name', '').strip()
    )
    db.session.add(group)
    db.session.commit()
    
    return jsonify({
        'id': group.id,
        'name': group.name,
        'manager_name': group.manager_name,
        'project_name': group.project_name
    }), 201


@api_bp.route('/groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """Delete a research group and all its entries."""
    group = db.session.get(ResearchGroup, group_id)
    if not group:
        return jsonify({'error': 'Research group not found'}), 404
    
    db.session.delete(group)
    db.session.commit()
    
    return jsonify({'message': 'Group deleted successfully'}), 200


@api_bp.route('/entries', methods=['POST'])
def create_entry():
    """Create a new time entry with time block."""
    data = request.get_json()
    
    # Validate required fields
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    if not data.get('research_group_id'):
        return jsonify({'error': 'research_group_id required'}), 400
    if not data.get('task_description'):
        return jsonify({'error': 'task_description required'}), 400
    if not data.get('start_time'):
        return jsonify({'error': 'start_time required'}), 400
    if not data.get('end_time'):
        return jsonify({'error': 'end_time required'}), 400
    
    # Validate research group exists
    group = db.session.get(ResearchGroup, data['research_group_id'])
    if not group:
        return jsonify({'error': 'Research group not found'}), 400
    
    # Parse times
    try:
        start_time = time.fromisoformat(data['start_time'])
        end_time = time.fromisoformat(data['end_time'])
    except ValueError as e:
        return jsonify({'error': f'Invalid time format: {str(e)}'}), 400
    
    # Validate end_time > start_time
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    if end_minutes <= start_minutes:
        return jsonify({'error': 'end_time must be after start_time'}), 400
    
    # Parse date (default to today)
    try:
        if data.get('date'):
            entry_date = datetime.fromisoformat(data['date']).date()
        else:
            entry_date = datetime.now().date()
    except ValueError as e:
        return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
    
    # Calculate hours
    total_hours = round((end_minutes - start_minutes) / 60.0, 2)
    
    # Create entry
    entry = TimeEntry(
        research_group_id=data['research_group_id'],
        date=entry_date,
        task_description=data['task_description'].strip(),
        total_hours=total_hours
    )
    db.session.add(entry)
    db.session.flush()
    
    # Create time block
    block = TimeBlock(
        time_entry_id=entry.id,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(block)
    db.session.commit()
    
    return jsonify({
        'id': entry.id,
        'date': entry.date.isoformat(),
        'task_description': entry.task_description,
        'total_hours': entry.total_hours
    }), 201
