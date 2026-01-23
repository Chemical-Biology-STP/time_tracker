"""Unit tests for REST API endpoints."""
import pytest
from datetime import date

from app import create_app, db
from app.models import ResearchGroup, TimeEntry, TimeBlock


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_group(app):
    """Create a sample research group for testing."""
    with app.app_context():
        group = ResearchGroup(
            name='Test Research Group',
            manager_name='John Doe',
            project_name='Test Project'
        )
        db.session.add(group)
        db.session.commit()
        return group.id


class TestHealthEndpoint:
    """Tests for GET /api/health endpoint."""
    
    def test_health_returns_ok(self, client):
        """Health check should return status ok."""
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json == {'status': 'ok'}


class TestGroupsEndpoint:
    """Tests for GET /api/groups endpoint."""
    
    def test_get_groups_empty(self, client):
        """Should return empty array when no groups exist."""
        response = client.get('/api/groups')
        assert response.status_code == 200
        assert response.json == []
    
    def test_get_groups_returns_correct_format(self, client, app):
        """Should return groups with id, name, manager_name, project_name."""
        with app.app_context():
            group = ResearchGroup(
                name='Research Team A',
                manager_name='Jane Smith',
                project_name='Project Alpha'
            )
            db.session.add(group)
            db.session.commit()
            group_id = group.id
        
        response = client.get('/api/groups')
        assert response.status_code == 200
        assert len(response.json) == 1
        
        group_data = response.json[0]
        assert group_data['id'] == group_id
        assert group_data['name'] == 'Research Team A'
        assert group_data['manager_name'] == 'Jane Smith'
        assert group_data['project_name'] == 'Project Alpha'
    
    def test_get_groups_multiple(self, client, app):
        """Should return all groups."""
        with app.app_context():
            for i in range(3):
                group = ResearchGroup(
                    name=f'Group {i}',
                    manager_name=f'Manager {i}',
                    project_name=f'Project {i}'
                )
                db.session.add(group)
            db.session.commit()
        
        response = client.get('/api/groups')
        assert response.status_code == 200
        assert len(response.json) == 3


class TestEntriesEndpoint:
    """Tests for POST /api/entries endpoint."""
    
    def test_create_entry_success(self, client, sample_group):
        """Should create entry and return 201 with entry data."""
        response = client.post('/api/entries', json={
            'research_group_id': sample_group,
            'task_description': 'Working on feature',
            'date': '2025-01-15',
            'start_time': '09:00',
            'end_time': '10:30'
        })
        
        assert response.status_code == 201
        data = response.json
        assert data['task_description'] == 'Working on feature'
        assert data['date'] == '2025-01-15'
        assert data['total_hours'] == 1.5
        assert 'id' in data
    
    def test_create_entry_missing_group_id(self, client):
        """Should return 400 when research_group_id is missing."""
        response = client.post('/api/entries', json={
            'task_description': 'Test task',
            'start_time': '09:00',
            'end_time': '10:00'
        })
        
        assert response.status_code == 400
        assert 'research_group_id' in response.json['error']
    
    def test_create_entry_missing_task_description(self, client, sample_group):
        """Should return 400 when task_description is missing."""
        response = client.post('/api/entries', json={
            'research_group_id': sample_group,
            'start_time': '09:00',
            'end_time': '10:00'
        })
        
        assert response.status_code == 400
        assert 'task_description' in response.json['error']
    
    def test_create_entry_missing_times(self, client, sample_group):
        """Should return 400 when start_time or end_time is missing."""
        response = client.post('/api/entries', json={
            'research_group_id': sample_group,
            'task_description': 'Test task'
        })
        
        assert response.status_code == 400
        assert 'start_time' in response.json['error']
    
    def test_create_entry_invalid_group(self, client):
        """Should return 400 when research group doesn't exist."""
        response = client.post('/api/entries', json={
            'research_group_id': 9999,
            'task_description': 'Test task',
            'start_time': '09:00',
            'end_time': '10:00'
        })
        
        assert response.status_code == 400
        assert 'not found' in response.json['error']
    
    def test_create_entry_end_before_start(self, client, sample_group):
        """Should return 400 when end_time is before start_time."""
        response = client.post('/api/entries', json={
            'research_group_id': sample_group,
            'task_description': 'Test task',
            'start_time': '10:00',
            'end_time': '09:00'
        })
        
        assert response.status_code == 400
        assert 'end_time must be after start_time' in response.json['error']
    
    def test_create_entry_creates_time_block(self, client, app, sample_group):
        """Should create associated TimeBlock record."""
        response = client.post('/api/entries', json={
            'research_group_id': sample_group,
            'task_description': 'Test task',
            'date': '2025-01-15',
            'start_time': '14:00',
            'end_time': '15:30'
        })
        
        assert response.status_code == 201
        entry_id = response.json['id']
        
        with app.app_context():
            entry = db.session.get(TimeEntry, entry_id)
            assert len(entry.time_blocks) == 1
            block = entry.time_blocks[0]
            assert block.start_time.hour == 14
            assert block.start_time.minute == 0
            assert block.end_time.hour == 15
            assert block.end_time.minute == 30
    
    def test_create_entry_default_date(self, client, app, sample_group):
        """Should use today's date when date is not provided."""
        response = client.post('/api/entries', json={
            'research_group_id': sample_group,
            'task_description': 'Test task',
            'start_time': '09:00',
            'end_time': '10:00'
        })
        
        assert response.status_code == 201
        assert response.json['date'] == date.today().isoformat()
