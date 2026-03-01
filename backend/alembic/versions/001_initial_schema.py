"""Initial database schema

Revision ID: initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('passport_country', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_is_verified'), 'users', ['is_verified'], unique=False)
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)

    # User preferences table
    op.create_table('user_preferences',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('budget_daily', sa.Float(), nullable=True),
        sa.Column('budget_total', sa.Float(), nullable=True),
        sa.Column('travel_style', sa.String(), nullable=True),
        sa.Column('interests', sa.Text(), nullable=True),
        sa.Column('preferred_weather', sa.String(), nullable=True),
        sa.Column('avoid_weather', sa.String(), nullable=True),
        sa.Column('passport_country', sa.String(), nullable=True),
        sa.Column('visa_preference', sa.String(), nullable=True),
        sa.Column('max_flight_duration', sa.Integer(), nullable=True),
        sa.Column('traveling_with', sa.String(), nullable=True),
        sa.Column('accessibility_needs', sa.Text(), nullable=True),
        sa.Column('dietary_restrictions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_preferences_user_id'), 'user_preferences', ['user_id'], unique=True)
    op.create_index(op.f('ix_user_preferences_travel_style'), 'user_preferences', ['travel_style'], unique=False)
    op.create_index(op.f('ix_user_preferences_visa_preference'), 'user_preferences', ['visa_preference'], unique=False)
    op.create_index(op.f('ix_user_preferences_created_at'), 'user_preferences', ['created_at'], unique=False)

    # Travel bookings table
    op.create_table('travel_bookings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('destination_id', sa.String(), nullable=False),
        sa.Column('destination_name', sa.String(), nullable=False),
        sa.Column('destination_country', sa.String(), nullable=False),
        sa.Column('travel_start', sa.DateTime(), nullable=False),
        sa.Column('travel_end', sa.DateTime(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('booking_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_travel_bookings_user_id'), 'travel_bookings', ['user_id'], unique=False)
    op.create_index(op.f('ix_travel_bookings_destination_id'), 'travel_bookings', ['destination_id'], unique=False)
    op.create_index(op.f('ix_travel_bookings_status'), 'travel_bookings', ['status'], unique=False)

    # Search history table
    op.create_table('search_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('origin', sa.String(), nullable=False),
        sa.Column('destination', sa.String(), nullable=True),
        sa.Column('travel_start', sa.DateTime(), nullable=True),
        sa.Column('travel_end', sa.DateTime(), nullable=True),
        sa.Column('search_query', sa.Text(), nullable=False),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_search_history_user_id'), 'search_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_search_history_origin'), 'search_history', ['origin'], unique=False)
    op.create_index(op.f('ix_search_history_destination'), 'search_history', ['destination'], unique=False)
    op.create_index(op.f('ix_search_history_created_at'), 'search_history', ['created_at'], unique=False)

    # Saved destinations table
    op.create_table('saved_destinations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('destination_id', sa.String(), nullable=False),
        sa.Column('destination_name', sa.String(), nullable=False),
        sa.Column('destination_country', sa.String(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_destinations_user_id'), 'saved_destinations', ['user_id'], unique=False)
    op.create_index(op.f('ix_saved_destinations_destination_id'), 'saved_destinations', ['destination_id'], unique=False)
    op.create_index(op.f('ix_saved_destinations_created_at'), 'saved_destinations', ['created_at'], unique=False)

    # Itineraries table
    op.create_table('itineraries',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('destination_id', sa.String(), nullable=False),
        sa.Column('destination_name', sa.String(), nullable=False),
        sa.Column('destination_country', sa.String(), nullable=False),
        sa.Column('travel_start', sa.DateTime(), nullable=False),
        sa.Column('travel_end', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_itineraries_user_id'), 'itineraries', ['user_id'], unique=False)

    # Itinerary days table
    op.create_table('itinerary_days',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('itinerary_id', sa.String(), nullable=True),
        sa.Column('day_number', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['itinerary_id'], ['itineraries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_itinerary_days_itinerary_id'), 'itinerary_days', ['itinerary_id'], unique=False)

    # Itinerary activities table
    op.create_table('itinerary_activities',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('day_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('activity_type', sa.String(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('location_name', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('booking_reference', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['day_id'], ['itinerary_days.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_itinerary_activities_day_id'), 'itinerary_activities', ['day_id'], unique=False)

    # Research jobs table
    op.create_table('research_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('query_params', sa.Text(), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=True),
        sa.Column('completed_steps', sa.Integer(), nullable=True),
        sa.Column('current_step', sa.String(), nullable=True),
        sa.Column('results', sa.Text(), nullable=True),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_research_jobs_user_id'), 'research_jobs', ['user_id'], unique=False)
    op.create_index(op.f('ix_research_jobs_job_type'), 'research_jobs', ['job_type'], unique=False)
    op.create_index(op.f('ix_research_jobs_status'), 'research_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('research_jobs')
    op.drop_table('itinerary_activities')
    op.drop_table('itinerary_days')
    op.drop_table('itineraries')
    op.drop_table('saved_destinations')
    op.drop_table('search_history')
    op.drop_table('travel_bookings')
    op.drop_table('user_preferences')
    op.drop_table('users')
