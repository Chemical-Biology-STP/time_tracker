"""Flask route handlers for Time Tracker."""
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from .models import db, ResearchGroup, TimeEntry, TimeBlock
from .utils import (
    validate_group_name,
    validate_task_description,
    validate_time_block,
    parse_time_blocks_from_form,
    calculate_total_hours_from_blocks,
)

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Redirect to groups page."""
    return redirect(url_for('main.groups'))


@bp.route('/groups', methods=['GET', 'POST'])
def groups():
    """List all research groups and handle group creation."""
    if request.method == 'POST':
        name = request.form.get('name', '')
        manager_name = request.form.get('manager_name', '')
        project_name = request.form.get('project_name', '')

        if not validate_group_name(name):
            flash('Group name cannot be empty.', 'error')
            return redirect(url_for('main.groups'))

        group = ResearchGroup(
            name=name.strip(),
            manager_name=manager_name.strip(),
            project_name=project_name.strip()
        )
        db.session.add(group)
        db.session.commit()
        flash('Research group created successfully.', 'success')
        return redirect(url_for('main.groups'))

    all_groups = ResearchGroup.query.all()
    return render_template('groups.html', groups=all_groups)


@bp.route('/groups/<int:group_id>/entries', methods=['GET', 'POST'])
def entries(group_id):
    """List entries for a group and handle entry creation."""
    group = ResearchGroup.query.get_or_404(group_id)

    if request.method == 'POST':
        task_description = request.form.get('task_description', '')
        date_str = request.form.get('date', '')

        if not validate_task_description(task_description):
            flash('Task description cannot be empty.', 'error')
            return redirect(url_for('main.entries', group_id=group_id))

        # Parse date
        try:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('main.entries', group_id=group_id))

        # Parse time blocks from form
        time_blocks = parse_time_blocks_from_form(request.form)

        # Validate at least one complete time block is provided
        if not time_blocks:
            flash('At least one complete time block is required.', 'error')
            return redirect(url_for('main.entries', group_id=group_id))

        # Validate each time block (end > start)
        for start, end in time_blocks:
            if not validate_time_block(start, end):
                flash('Time block end time must be after start time.', 'error')
                return redirect(url_for('main.entries', group_id=group_id))

        # Calculate total hours from all blocks
        total_hours = calculate_total_hours_from_blocks(time_blocks)

        # Create TimeEntry first
        entry = TimeEntry(
            research_group_id=group_id,
            date=entry_date,
            task_description=task_description.strip(),
            total_hours=total_hours
        )
        db.session.add(entry)
        db.session.flush()  # Get the entry ID

        # Create TimeBlock records
        for start, end in time_blocks:
            block = TimeBlock(
                time_entry_id=entry.id,
                start_time=start,
                end_time=end
            )
            db.session.add(block)

        db.session.commit()
        flash('Time entry added successfully.', 'success')
        return redirect(url_for('main.entries', group_id=group_id))

    # Get entries ordered by date descending
    all_entries = TimeEntry.query.filter_by(research_group_id=group_id).order_by(TimeEntry.date.desc()).all()
    return render_template('entries.html', group=group, entries=all_entries)


@bp.route('/groups/<int:group_id>/summary')
def summary(group_id):
    """Display summary for a research group."""
    group = ResearchGroup.query.get_or_404(group_id)
    entries = TimeEntry.query.filter_by(research_group_id=group_id).order_by(TimeEntry.date.desc()).all()

    total_hours = group.get_total_hours()
    total_pay = group.get_total_pay()

    return render_template(
        'summary.html',
        group=group,
        entries=entries,
        total_hours=total_hours,
        total_pay=total_pay
    )


@bp.route('/entries/<int:entry_id>/delete', methods=['POST'])
def delete_entry(entry_id):
    """Delete a time entry with cascade to time blocks."""
    entry = TimeEntry.query.get_or_404(entry_id)
    group_id = entry.research_group_id
    
    db.session.delete(entry)
    db.session.commit()
    
    flash('Time entry deleted successfully.', 'success')
    return redirect(url_for('main.entries', group_id=group_id))
