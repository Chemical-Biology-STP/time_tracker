# Implementation Plan: Flask Time Tracker

## Overview

Minimal implementation of a Flask time tracking application with SQLite persistence. Tasks are structured to build incrementally with core functionality first.

## Tasks

- [x] 1. Set up Flask application with SQLAlchemy models
  - Create `app/__init__.py` with Flask app factory and SQLite configuration
  - Create `app/models.py` with ResearchGroup and TimeEntry models
  - Add Flask and Flask-SQLAlchemy to pixi.toml dependencies
  - Initialize database with tables
  - _Requirements: 1.1, 2.1_

- [x] 2. Implement validation and calculation functions
  - Create `app/utils.py` with validation functions (empty string, time block)
  - Implement `calculate_block_hours()` and `calculate_total_hours()` functions
  - Implement `calculate_pay()` function with rate 107.93
  - _Requirements: 1.3, 2.4, 2.5, 3.1, 3.3, 5.2_

- [x] 3. Implement routes and templates
  - [x] 3.1 Create base template and research group routes
    - Create `app/templates/base.html` with minimal styling
    - Create `app/routes.py` with group list (GET /groups) and create (POST /groups) routes
    - Create `app/templates/groups.html` for listing and creating groups
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [x] 3.2 Create time entry routes and templates
    - Add entry list (GET /groups/<id>/entries) and create (POST /groups/<id>/entries) routes
    - Create `app/templates/entries.html` for viewing and adding entries
    - Entries ordered by date descending
    - _Requirements: 2.1, 2.2, 2.3, 4.1, 4.2, 4.3_
  
  - [x] 3.3 Create summary route and template
    - Add summary route (GET /groups/<id>/summary)
    - Create `app/templates/summary.html` showing total hours and pay
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 4. Create application entry point
  - Create `run.py` to run the Flask application
  - Add run task to pixi.toml
  - _Requirements: All_

- [x] 5. Checkpoint - Verify application works
  - Ensure application runs without errors
  - Test basic flows: create group, add entry, view summary

## Notes

- Uses SQLite for simplicity (no external database setup)
- Minimal styling with inline CSS in base template
- All validation happens server-side in route handlers
