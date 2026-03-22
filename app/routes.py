"""Flask route handlers for Time Tracker."""
import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from .models import db, ResearchGroup, Project, TimeEntry, TimeBlock
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


@bp.route('/groups/<int:group_id>/projects', methods=['POST'])
def create_project(group_id):
    """Create a new project under a research group."""
    group = ResearchGroup.query.get_or_404(group_id)
    name = request.form.get('project_name_new', '').strip()
    if not name:
        flash('Project name cannot be empty.', 'error')
    else:
        project = Project(name=name, research_group_id=group_id)
        db.session.add(project)
        db.session.commit()
        flash(f'Project "{name}" created.', 'success')
    return redirect(url_for('main.groups'))


@bp.route('/projects/<int:project_id>/archive', methods=['POST'])
def archive_project(project_id):
    """Toggle archive status of a project."""
    project = Project.query.get_or_404(project_id)
    project.archived = not project.archived
    db.session.commit()
    status = 'archived' if project.archived else 'unarchived'
    flash(f'Project "{project.name}" {status}.', 'success')
    return redirect(url_for('main.groups'))


@bp.route('/projects/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """Delete a project."""
    project = Project.query.get_or_404(project_id)
    name = project.name
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{name}" deleted.', 'success')
    return redirect(url_for('main.groups'))


@bp.route('/calendar')
def overall_calendar():
    """Display an overall calendar view across all groups."""
    from calendar import monthrange, monthcalendar
    
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    start_date = datetime(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day).date()
    
    entries = TimeEntry.query.filter(
        TimeEntry.date >= start_date,
        TimeEntry.date <= end_date
    ).order_by(TimeEntry.date.asc()).all()
    
    entries_by_day = {}
    hours_by_day = {}
    for entry in entries:
        day = entry.date.day
        if day not in entries_by_day:
            entries_by_day[day] = []
            hours_by_day[day] = 0
        entries_by_day[day].append(entry)
        hours_by_day[day] += entry.total_hours
    
    # Sort entries within each day by first time block start time
    for day in entries_by_day:
        entries_by_day[day].sort(
            key=lambda e: e.get_sorted_time_blocks()[0].start_time if e.get_sorted_time_blocks() else e.id
        )
    
    weeks = monthcalendar(year, month)
    month_name = datetime(year, month, 1).strftime('%B %Y')
    
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    
    return render_template(
        'overall_calendar.html',
        weeks=weeks,
        entries_by_day=entries_by_day,
        hours_by_day=hours_by_day,
        month_name=month_name,
        year=year,
        month=month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        today=now.day if year == now.year and month == now.month else None
    )


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
            project_id=request.form.get('project_id') or None,
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
    project_filter = request.args.get('project', '')
    
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
    
    if project_filter:
        if project_filter == 'none':
            query = query.filter(TimeEntry.project_id.is_(None))
        else:
            try:
                query = query.filter(TimeEntry.project_id == int(project_filter))
            except (ValueError, TypeError):
                pass
    
    all_entries = query.order_by(TimeEntry.date.desc()).all()
    
    # Get available months for filter dropdown
    all_dates = db.session.query(TimeEntry.date).filter_by(research_group_id=group_id).distinct().all()
    available_months = sorted(set(d[0].strftime('%Y-%m') for d in all_dates), reverse=True)
    
    # Get all projects for this group (active for form, all for filter)
    projects = Project.query.filter_by(research_group_id=group_id, archived=False).all()
    all_projects = Project.query.filter_by(research_group_id=group_id).all()
    
    return render_template('entries.html', group=group, entries=all_entries, 
                          month_filter=month_filter, available_months=available_months,
                          projects=projects, all_projects=all_projects,
                          project_filter=project_filter)


@bp.route('/summary')
def overall_summary():
    """Display overall summary with hours broken down by group and project."""
    from calendar import monthrange
    
    year_filter = request.args.get('year', '', type=str)
    month_filter = request.args.get('month', '', type=str)
    
    # Parse filters
    try:
        year_val = int(year_filter) if year_filter else None
    except (ValueError, TypeError):
        year_val = None
    try:
        month_val = int(month_filter) if month_filter else None
    except (ValueError, TypeError):
        month_val = None
    
    # Build query with filters
    query = TimeEntry.query
    if year_val and month_val:
        start_date = datetime(year_val, month_val, 1).date()
        _, last_day = monthrange(year_val, month_val)
        end_date = datetime(year_val, month_val, last_day).date()
        query = query.filter(TimeEntry.date >= start_date, TimeEntry.date <= end_date)
    elif year_val:
        start_date = datetime(year_val, 1, 1).date()
        end_date = datetime(year_val, 12, 31).date()
        query = query.filter(TimeEntry.date >= start_date, TimeEntry.date <= end_date)
    
    entries = query.all()
    all_groups = ResearchGroup.query.all()
    
    # Available years/months for filter dropdowns
    all_dates = db.session.query(TimeEntry.date).distinct().all()
    available_years = sorted(set(d[0].year for d in all_dates), reverse=True)
    available_months = list(range(1, 13))
    
    total_hours = sum(e.total_hours for e in entries)
    total_pay = round(total_hours * 107.93, 2)
    
    group_map = {g.id: g for g in all_groups}
    
    # Hours by group
    group_breakdown = []
    for g in all_groups:
        g_entries = [e for e in entries if e.research_group_id == g.id]
        g_hours = sum(e.total_hours for e in g_entries)
        if g_hours > 0:
            group_breakdown.append({
                'id': g.id,
                'name': g.name,
                'hours': round(g_hours, 2),
                'pay': round(g_hours * 107.93, 2),
                'entries': len(g_entries),
                'pct': round(g_hours / total_hours * 100, 1) if total_hours > 0 else 0
            })
    group_breakdown.sort(key=lambda x: x['hours'], reverse=True)
    
    # Hours by project, grouped by research group
    all_projects = Project.query.all()
    
    # Build project rows
    project_rows = []
    for p in all_projects:
        p_entries = [e for e in entries if e.project_id == p.id]
        p_hours = sum(e.total_hours for e in p_entries)
        if p_hours > 0:
            g = group_map.get(p.research_group_id)
            project_rows.append({
                'name': p.name,
                'group_name': g.name if g else 'Unknown',
                'group_id': p.research_group_id,
                'hours': round(p_hours, 2),
                'pay': round(p_hours * 107.93, 2),
                'entries': len(p_entries),
                'pct': round(p_hours / total_hours * 100, 1) if total_hours > 0 else 0,
                'archived': p.archived,
                'is_unassigned': False,
                'unassigned_items': []
            })
    
    # Unassigned entries per group (with detail items)
    unassigned_by_group = {}
    for e in entries:
        if not e.project_id:
            gid = e.research_group_id
            if gid not in unassigned_by_group:
                unassigned_by_group[gid] = {'hours': 0, 'entries': 0, 'items': []}
            unassigned_by_group[gid]['hours'] += e.total_hours
            unassigned_by_group[gid]['entries'] += 1
            unassigned_by_group[gid]['items'].append({
                'date': e.date.strftime('%Y-%m-%d'),
                'task': e.task_description,
                'hours': round(e.total_hours, 2)
            })
    
    for gid, data in unassigned_by_group.items():
        g = group_map.get(gid)
        project_rows.append({
            'name': '(No project)',
            'group_name': g.name if g else 'Unknown',
            'group_id': gid,
            'hours': round(data['hours'], 2),
            'pay': round(data['hours'] * 107.93, 2),
            'entries': data['entries'],
            'pct': round(data['hours'] / total_hours * 100, 1) if total_hours > 0 else 0,
            'archived': False,
            'is_unassigned': True,
            'unassigned_items': sorted(data['items'], key=lambda x: x['date'], reverse=True)
        })
    
    # Sort: group by group_name, then by hours desc within each group
    project_rows.sort(key=lambda x: (-sum(r['hours'] for r in project_rows if r['group_id'] == x['group_id']), x['group_name'], -x['hours']))
    
    # Period label
    if year_val and month_val:
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        period_label = f"{month_names[month_val]} {year_val}"
    elif year_val:
        period_label = str(year_val)
    else:
        period_label = "All Time"
    
    return render_template('overall_summary.html',
                          total_hours=total_hours,
                          total_pay=total_pay,
                          total_entries=len(entries),
                          group_breakdown=group_breakdown,
                          project_rows=project_rows,
                          available_years=available_years,
                          available_months=available_months,
                          year_filter=year_filter,
                          month_filter=month_filter,
                          period_label=period_label)


@bp.route('/groups/<int:group_id>/summary')
def summary(group_id):
    """Display summary dashboard for a research group."""
    group = ResearchGroup.query.get_or_404(group_id)
    entries = TimeEntry.query.filter_by(research_group_id=group_id).order_by(TimeEntry.date.asc()).all()

    total_hours = group.get_total_hours()
    total_pay = group.get_total_pay()
    
    # Daily hours for heatmap and charts
    daily_hours = {}
    for entry in entries:
        date_str = entry.date.strftime('%Y-%m-%d')
        daily_hours[date_str] = daily_hours.get(date_str, 0) + entry.total_hours
    
    # Weekly hours (ISO week)
    weekly_hours = {}
    for entry in entries:
        iso = entry.date.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"
        weekly_hours[week_key] = weekly_hours.get(week_key, 0) + entry.total_hours
    
    # Monthly breakdown
    monthly_data = {}
    for entry in entries:
        month_key = entry.date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {'hours': 0, 'entries': 0}
        monthly_data[month_key]['hours'] += entry.total_hours
        monthly_data[month_key]['entries'] += 1
    
    # Stats
    num_entries = len(entries)
    days_worked = len(daily_hours)
    avg_hours_per_day = round(total_hours / days_worked, 2) if days_worked > 0 else 0
    
    # Project breakdown within this group
    projects = Project.query.filter_by(research_group_id=group_id).all()
    project_breakdown = []
    unassigned_hours = 0
    unassigned_entries = 0
    for entry in entries:
        if not entry.project_id:
            unassigned_hours += entry.total_hours
            unassigned_entries += 1
    
    for p in projects:
        p_hours = sum(e.total_hours for e in entries if e.project_id == p.id)
        p_count = sum(1 for e in entries if e.project_id == p.id)
        if p_hours > 0 or p_count > 0:
            project_breakdown.append({
                'name': p.name,
                'hours': round(p_hours, 2),
                'pay': round(p_hours * 107.93, 2),
                'entries': p_count,
                'pct': round(p_hours / total_hours * 100, 1) if total_hours > 0 else 0,
                'archived': p.archived
            })
    project_breakdown.sort(key=lambda x: x['hours'], reverse=True)
    
    if unassigned_hours > 0:
        project_breakdown.append({
            'name': '(No project)',
            'hours': round(unassigned_hours, 2),
            'pay': round(unassigned_hours * 107.93, 2),
            'entries': unassigned_entries,
            'pct': round(unassigned_hours / total_hours * 100, 1) if total_hours > 0 else 0,
            'archived': False
        })

    return render_template(
        'summary.html',
        group=group,
        entries=entries,
        total_hours=total_hours,
        total_pay=total_pay,
        daily_hours=daily_hours,
        weekly_hours=weekly_hours,
        monthly_data=monthly_data,
        num_entries=num_entries,
        days_worked=days_worked,
        avg_hours_per_day=avg_hours_per_day,
        project_breakdown=project_breakdown
    )


@bp.route('/groups/<int:group_id>/calendar')
def calendar_view(group_id):
    """Display calendar view of entries for a research group."""
    from calendar import monthrange, monthcalendar
    
    group = ResearchGroup.query.get_or_404(group_id)
    
    # Get year/month from query params, default to current
    now = datetime.now()
    year = request.args.get('year', now.year, type=int)
    month = request.args.get('month', now.month, type=int)
    
    # Clamp values
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    # Get entries for this month
    start_date = datetime(year, month, 1).date()
    _, last_day = monthrange(year, month)
    end_date = datetime(year, month, last_day).date()
    
    entries = TimeEntry.query.filter_by(research_group_id=group_id).filter(
        TimeEntry.date >= start_date,
        TimeEntry.date <= end_date
    ).order_by(TimeEntry.date.asc()).all()
    
    # Group entries by day
    entries_by_day = {}
    hours_by_day = {}
    for entry in entries:
        day = entry.date.day
        if day not in entries_by_day:
            entries_by_day[day] = []
            hours_by_day[day] = 0
        entries_by_day[day].append(entry)
        hours_by_day[day] += entry.total_hours
    
    # Sort entries within each day by first time block start time
    for day in entries_by_day:
        entries_by_day[day].sort(
            key=lambda e: e.get_sorted_time_blocks()[0].start_time if e.get_sorted_time_blocks() else e.id
        )
    
    # Get calendar weeks
    weeks = monthcalendar(year, month)
    
    # Month name
    month_name = datetime(year, month, 1).strftime('%B %Y')
    
    # Prev/next month
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
    
    return render_template(
        'calendar.html',
        group=group,
        weeks=weeks,
        entries_by_day=entries_by_day,
        hours_by_day=hours_by_day,
        month_name=month_name,
        year=year,
        month=month,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        today=now.day if year == now.year and month == now.month else None
    )


@bp.route('/groups/<int:group_id>/export')
def export_entries(group_id):
    """Export entries to CSV file."""
    group = ResearchGroup.query.get_or_404(group_id)
    
    # Get month filter from query params
    month_filter = request.args.get('month', '')
    
    # Hourly rate for calculating amount (can be overridden via query param)
    hourly_rate = request.args.get('rate', 107.93, type=float)
    
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
    
    # Create CSV matching Chrome extension format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Group', 'Project', 'Manager', 'Task', 'Start', 'End', 'Hours', 'Amount (£)'])
    
    for entry in entries:
        # Get first time block for start/end times
        time_blocks = entry.get_sorted_time_blocks()
        if time_blocks:
            start_time = time_blocks[0].start_time.strftime('%H:%M')
            end_time = time_blocks[-1].end_time.strftime('%H:%M')
        else:
            start_time = ''
            end_time = ''
        
        amount = entry.total_hours * hourly_rate
        
        writer.writerow([
            entry.date.strftime('%Y-%m-%d'),
            group.name,
            entry.project.name if entry.project else group.project_name,
            group.manager_name,
            entry.task_description,
            start_time,
            end_time,
            f"{entry.total_hours:.2f}",
            f"{amount:.2f}"
        ])
    
    # Add total row
    total_hours = sum(e.total_hours for e in entries)
    total_amount = total_hours * hourly_rate
    writer.writerow([])
    writer.writerow(['', '', '', '', '', '', 'Total', f"{total_hours:.2f}", f"{total_amount:.2f}"])
    
    output.seek(0)
    
    # Generate filename
    filename = f"{group.name.replace(' ', '_')}_entries"
    if month_filter:
        filename += f"_{month_filter}"
    filename += ".csv"
    
    # Add UTF-8 BOM for Excel compatibility
    csv_content = '\ufeff' + output.getvalue()
    
    return Response(
        csv_content,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@bp.route('/groups/<int:group_id>/export-excel')
def export_excel(group_id):
    """Export entries to Excel file, optionally with monthly sheets for a year."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from calendar import monthrange, month_name as cal_month_name
    
    group = ResearchGroup.query.get_or_404(group_id)
    hourly_rate = request.args.get('rate', 107.93, type=float)
    year_filter = request.args.get('year', '', type=str)
    month_filter = request.args.get('month', '')
    
    # Parse year safely
    try:
        year_filter = int(year_filter) if year_filter else None
    except (ValueError, TypeError):
        year_filter = None
    
    wb = Workbook()
    
    headers = ['Date', 'Group', 'Project', 'Manager', 'Task', 'Start', 'End', 'Hours', 'Amount (£)']
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    total_font = Font(bold=True, size=11)
    currency_fmt = '£#,##0.00'
    thin_border = Border(bottom=Side(style='thin', color='DDDDDD'))
    
    def write_entries_to_sheet(ws, entries, sheet_title=None):
        """Write entries to a worksheet with formatting."""
        if sheet_title:
            ws.title = sheet_title
        
        # Headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='left')
        
        # Data rows
        for row_idx, entry in enumerate(entries, 2):
            time_blocks = entry.get_sorted_time_blocks()
            start_time = time_blocks[0].start_time.strftime('%H:%M') if time_blocks else ''
            end_time = time_blocks[-1].end_time.strftime('%H:%M') if time_blocks else ''
            amount = entry.total_hours * hourly_rate
            
            ws.cell(row=row_idx, column=1, value=entry.date.strftime('%Y-%m-%d'))
            ws.cell(row=row_idx, column=2, value=group.name)
            ws.cell(row=row_idx, column=3, value=entry.project.name if entry.project else group.project_name)
            ws.cell(row=row_idx, column=4, value=group.manager_name)
            ws.cell(row=row_idx, column=5, value=entry.task_description)
            ws.cell(row=row_idx, column=6, value=start_time)
            ws.cell(row=row_idx, column=7, value=end_time)
            ws.cell(row=row_idx, column=8, value=round(entry.total_hours, 2))
            cell = ws.cell(row=row_idx, column=9, value=round(amount, 2))
            cell.number_format = currency_fmt
            
            for col in range(1, 10):
                ws.cell(row=row_idx, column=col).border = thin_border
        
        # Totals row
        if entries:
            total_row = len(entries) + 3
            total_hours = sum(e.total_hours for e in entries)
            total_amount = total_hours * hourly_rate
            
            ws.cell(row=total_row, column=7, value='Total').font = total_font
            ws.cell(row=total_row, column=8, value=round(total_hours, 2)).font = total_font
            cell = ws.cell(row=total_row, column=9, value=round(total_amount, 2))
            cell.font = total_font
            cell.number_format = currency_fmt
        
        # Auto-width columns
        for col in range(1, 10):
            max_len = len(headers[col - 1])
            for row in range(2, min(len(entries) + 2, 50)):
                val = ws.cell(row=row, column=col).value
                if val:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[chr(64 + col)].width = min(max_len + 3, 40)
    
    if year_filter:
        # Yearly export: one sheet per month
        wb.remove(wb.active)
        
        for m in range(1, 13):
            start_date = datetime(year_filter, m, 1).date()
            _, last_day = monthrange(year_filter, m)
            end_date = datetime(year_filter, m, last_day).date()
            
            month_entries = TimeEntry.query.filter_by(research_group_id=group_id).filter(
                TimeEntry.date >= start_date,
                TimeEntry.date <= end_date
            ).order_by(TimeEntry.date.asc()).all()
            
            if month_entries:
                ws = wb.create_sheet()
                write_entries_to_sheet(ws, month_entries, cal_month_name[m])
        
        # If no entries at all, add an empty sheet
        if len(wb.sheetnames) == 0:
            ws = wb.create_sheet('No Data')
            ws.cell(row=1, column=1, value='No entries found for this year.')
        
        filename = f"{group.name.replace(' ', '_')}_{year_filter}.xlsx"
    
    elif month_filter:
        # Single month export
        try:
            y, m = map(int, month_filter.split('-'))
            start_date = datetime(y, m, 1).date()
            _, last_day = monthrange(y, m)
            end_date = datetime(y, m, last_day).date()
            
            entries = TimeEntry.query.filter_by(research_group_id=group_id).filter(
                TimeEntry.date >= start_date,
                TimeEntry.date <= end_date
            ).order_by(TimeEntry.date.asc()).all()
        except (ValueError, TypeError):
            entries = []
        
        ws = wb.active
        write_entries_to_sheet(ws, entries, month_filter)
        filename = f"{group.name.replace(' ', '_')}_{month_filter}.xlsx"
    
    else:
        # All entries
        entries = TimeEntry.query.filter_by(research_group_id=group_id).order_by(TimeEntry.date.asc()).all()
        ws = wb.active
        write_entries_to_sheet(ws, entries, 'All Entries')
        filename = f"{group.name.replace(' ', '_')}_all.xlsx"
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
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
        new_group_id = request.form.get('research_group_id', type=int)
        new_project_id = request.form.get('project_id') or None

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
        if new_group_id:
            entry.research_group_id = new_group_id
        entry.project_id = int(new_project_id) if new_project_id else None

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
        return redirect(url_for('main.entries', group_id=entry.research_group_id))

    all_groups = ResearchGroup.query.all()
    # Get projects for the current group (for initial load)
    projects = Project.query.filter_by(research_group_id=group.id, archived=False).all()
    # Include the currently assigned project even if archived
    if entry.project_id and not any(p.id == entry.project_id for p in projects):
        current_project = db.session.get(Project, entry.project_id)
        if current_project:
            projects.append(current_project)

    return render_template('edit_entry.html', entry=entry, group=group,
                          all_groups=all_groups, projects=projects)


# ---------------------------------------------------------------------------
# ProjMgmt Sync Routes
# ---------------------------------------------------------------------------


@bp.route('/sync', methods=['GET'])
def sync_settings():
    """Display ProjMgmt sync configuration and status."""
    try:
        from .sync import _load_config
    except Exception:
        flash('Sync module not available.', 'error')
        return redirect(url_for('main.groups'))

    config = _load_config()
    groups = ResearchGroup.query.all()

    return render_template(
        'sync.html',
        config=config,
        groups=groups,
    )


@bp.route('/sync/configure', methods=['POST'])
def sync_configure():
    """Save ProjMgmt sync configuration and test connection."""
    server_url = request.form.get('server_url', '').strip()
    email = request.form.get('email', '').strip()

    if not server_url or not email:
        flash('Server URL and email are required.', 'error')
        return redirect(url_for('main.sync_settings'))

    try:
        from .sync import ProjMgmtSync, _load_config, _save_config

        config = _load_config()
        config['server_url'] = server_url
        config['email'] = email
        _save_config(config)

        sync = ProjMgmtSync(server_url, email)
        user_info = sync.authenticate()
        flash(f'Connected as {user_info["username"]} ({user_info["role"]}).', 'success')
    except Exception as exc:
        flash(f'Configuration saved but connection failed: {exc}', 'error')

    return redirect(url_for('main.sync_settings'))


@bp.route('/sync/initial-push', methods=['POST'])
def sync_initial_push():
    """Push all local labs, projects, and time logs to ProjMgmt (first-time setup)."""
    try:
        from .sync import ProjMgmtSync, _load_config, _save_config

        config = _load_config()
        if not config.get('server_url') or not config.get('email'):
            flash('Configure sync settings first.', 'error')
            return redirect(url_for('main.sync_settings'))

        sync_client = ProjMgmtSync(config['server_url'], config['email'])
        sync_client.authenticate()
        result = sync_client.push_initial()

        config['initial_sync_done'] = True
        _save_config(config)

        flash(
            f'Initial sync complete: {result.get("labs_created", 0)} labs, '
            f'{result.get("projects_created", 0)} projects, '
            f'{result.get("logs_created", 0)} time logs pushed.',
            'success',
        )
    except Exception as exc:
        flash(f'Initial sync failed: {exc}', 'error')

    return redirect(url_for('main.sync_settings'))


@bp.route('/sync/pull', methods=['POST'])
def sync_pull():
    """Pull new labs, projects, and tasks from ProjMgmt."""
    try:
        from .sync import ProjMgmtSync, _load_config, _save_config

        config = _load_config()
        if not config.get('server_url') or not config.get('email'):
            flash('Configure sync settings first.', 'error')
            return redirect(url_for('main.sync_settings'))

        sync_client = ProjMgmtSync(config['server_url'], config['email'])
        sync_client.authenticate()

        struct_result = sync_client.pull_structure()
        task_result = sync_client.pull_tasks()

        flash(
            f'Pull complete: {struct_result.get("labs_created", 0)} new labs, '
            f'{struct_result.get("projects_created", 0)} new projects, '
            f'{struct_result.get("projects_deleted", 0)} projects removed, '
            f'{task_result.get("tasks_created", 0)} new tasks, '
            f'{task_result.get("tasks_deleted", 0)} tasks removed.',
            'success',
        )
    except Exception as exc:
        flash(f'Pull failed: {exc}', 'error')

    return redirect(url_for('main.sync_settings'))


@bp.route('/sync/push', methods=['POST'])
def sync_push():
    """Push time logs to ProjMgmt."""
    since_date = request.form.get('since_date', '').strip() or None

    try:
        from .sync import ProjMgmtSync, _load_config, _save_config

        config = _load_config()
        if not config.get('server_url') or not config.get('email'):
            flash('Configure sync settings first.', 'error')
            return redirect(url_for('main.sync_settings'))

        sync_client = ProjMgmtSync(config['server_url'], config['email'])
        sync_client.authenticate()
        result = sync_client.push_time_logs(since_date)

        created = result.get('created', 0)
        updated = result.get('updated', 0)
        skipped = result.get('skipped', 0)
        errors = result.get('errors', [])

        msg = f'Push complete: {created} created, {updated} updated, {skipped} skipped.'
        if errors:
            msg += f' {len(errors)} error(s).'
        flash(msg, 'success' if not errors else 'warning')
    except Exception as exc:
        flash(f'Push failed: {exc}', 'error')

    return redirect(url_for('main.sync_settings'))


@bp.route('/sync/full', methods=['POST'])
def sync_full():
    """Run a full bidirectional sync (pull structure + push time logs)."""
    try:
        from .sync import ProjMgmtSync, _load_config, _save_config

        config = _load_config()
        if not config.get('server_url') or not config.get('email'):
            flash('Configure sync settings first.', 'error')
            return redirect(url_for('main.sync_settings'))

        sync_client = ProjMgmtSync(config['server_url'], config['email'])
        result = sync_client.full_sync(since=config.get('last_sync'))

        # Update last_sync
        server_time = result.get('pull', {}).get('server_time')
        if server_time:
            config['last_sync'] = server_time
            _save_config(config)

        pull = result.get('pull', {})
        push = result.get('push', {})
        flash(
            f'Full sync done — Pulled: {pull.get("labs_created", 0)} labs, '
            f'{pull.get("projects_created", 0)} projects. '
            f'Pushed: {push.get("created", 0)} created, {push.get("updated", 0)} updated.',
            'success',
        )
    except Exception as exc:
        flash(f'Sync failed: {exc}', 'error')

    return redirect(url_for('main.sync_settings'))


@bp.route('/sync/toggle-auto', methods=['POST'])
def sync_toggle_auto():
    """Enable or disable auto-sync."""
    try:
        from .sync import _load_config, _save_config, start_auto_sync, stop_auto_sync
        from flask import current_app

        config = _load_config()
        auto_enabled = config.get('auto_sync', False)

        if auto_enabled:
            stop_auto_sync()
            config['auto_sync'] = False
            flash('Auto-sync disabled.', 'success')
        else:
            start_auto_sync(current_app._get_current_object())
            config['auto_sync'] = True
            flash('Auto-sync enabled (every 5 minutes).', 'success')

        _save_config(config)
    except Exception as exc:
        flash(f'Failed to toggle auto-sync: {exc}', 'error')

    return redirect(url_for('main.sync_settings'))

