"""Flask route handlers for Time Tracker."""
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
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


@bp.route('/groups/<int:group_id>/delete', methods=['POST'])
def delete_group(group_id):
    """Delete a research group and all its entries."""
    group = ResearchGroup.query.get_or_404(group_id)
    db.session.delete(group)
    db.session.commit()
    flash('Research group deleted successfully.', 'success')
    return redirect(url_for('main.groups'))


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

    # Get month filter from query params
    month_filter = request.args.get('month', '')
    
    # Build query
    query = TimeEntry.query.filter_by(research_group_id=group_id)
    
    if month_filter:
        try:
            year, month = map(int, month_filter.split('-'))
            from calendar import monthrange
            start_date = datetime(year, month, 1).date()
            _, last_day = monthrange(year, month)
            end_date = datetime(year, month, last_day).date()
            query = query.filter(TimeEntry.date >= start_date, TimeEntry.date <= end_date)
        except (ValueError, TypeError):
            pass
    
    all_entries = query.order_by(TimeEntry.date.desc()).all()
    
    # Get available months for filter dropdown
    all_dates = db.session.query(TimeEntry.date).filter_by(research_group_id=group_id).distinct().all()
    available_months = sorted(set(d[0].strftime('%Y-%m') for d in all_dates), reverse=True)
    
    return render_template('entries.html', group=group, entries=all_entries, 
                          month_filter=month_filter, available_months=available_months)


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


@bp.route('/groups/<int:group_id>/export')
def export_entries(group_id):
    """Export entries to CSV file."""
    group = ResearchGroup.query.get_or_404(group_id)
    
    # Get month filter from query params
    month_filter = request.args.get('month', '')
    
    # Build query
    query = TimeEntry.query.filter_by(research_group_id=group_id)
    
    if month_filter:
        try:
            year, month = map(int, month_filter.split('-'))
            from calendar import monthrange
            start_date = datetime(year, month, 1).date()
            _, last_day = monthrange(year, month)
            end_date = datetime(year, month, last_day).date()
            query = query.filter(TimeEntry.date >= start_date, TimeEntry.date <= end_date)
        except (ValueError, TypeError):
            pass
    
    entries = query.order_by(TimeEntry.date.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Task Description', 'Time Blocks', 'Total Hours'])
    
    for entry in entries:
        time_blocks_str = '; '.join(
            f"{b.start_time.strftime('%H:%M')}-{b.end_time.strftime('%H:%M')}"
            for b in entry.get_sorted_time_blocks()
        )
        writer.writerow([
            entry.date.strftime('%Y-%m-%d'),
            entry.task_description,
            time_blocks_str,
            f"{entry.total_hours:.2f}"
        ])
    
    # Add total row
    total_hours = sum(e.total_hours for e in entries)
    writer.writerow([])
    writer.writerow(['', '', 'Total:', f"{total_hours:.2f}"])
    
    output.seek(0)
    
    # Generate filename
    filename = f"{group.name.replace(' ', '_')}_entries"
    if month_filter:
        filename += f"_{month_filter}"
    filename += ".csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
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


@bp.route('/entries/<int:entry_id>/edit', methods=['GET', 'POST'])
def edit_entry(entry_id):
    """Edit a time entry."""
    entry = TimeEntry.query.get_or_404(entry_id)
    group = entry.group

    if request.method == 'POST':
        task_description = request.form.get('task_description', '')
        date_str = request.form.get('date', '')

        if not validate_task_description(task_description):
            flash('Task description cannot be empty.', 'error')
            return redirect(url_for('main.edit_entry', entry_id=entry_id))

        # Parse date
        try:
            entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('main.edit_entry', entry_id=entry_id))

        # Parse time blocks from form
        time_blocks = parse_time_blocks_from_form(request.form)

        # Validate at least one complete time block is provided
        if not time_blocks:
            flash('At least one complete time block is required.', 'error')
            return redirect(url_for('main.edit_entry', entry_id=entry_id))

        # Validate each time block (end > start)
        for start, end in time_blocks:
            if not validate_time_block(start, end):
                flash('Time block end time must be after start time.', 'error')
                return redirect(url_for('main.edit_entry', entry_id=entry_id))

        # Calculate total hours from all blocks
        total_hours = calculate_total_hours_from_blocks(time_blocks)

        # Update entry
        entry.task_description = task_description.strip()
        entry.date = entry_date
        entry.total_hours = total_hours

        # Delete existing time blocks
        TimeBlock.query.filter_by(time_entry_id=entry.id).delete()

        # Create new TimeBlock records
        for start, end in time_blocks:
            block = TimeBlock(
                time_entry_id=entry.id,
                start_time=start,
                end_time=end
            )
            db.session.add(block)

        db.session.commit()
        flash('Time entry updated successfully.', 'success')
        return redirect(url_for('main.entries', group_id=group.id))

    return render_template('edit_entry.html', entry=entry, group=group)
