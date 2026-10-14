"""Initial schema for Market Profit microservice

Revision ID: 0001_initial_market_profit_schema
Revises: 
Create Date: 2026-10-14 19:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_market_profit'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Cultivation Budgets (Parent table, zero foreign dependencies)
    op.create_table(
        'cultivation_budgets',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('crop_id', sa.String(length=32), nullable=False),
        sa.Column('district_id', sa.String(length=10), nullable=False),
        sa.Column('season', sa.String(length=20), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('entry_mode', sa.String(length=20), server_default='detailed', nullable=False),
        sa.Column('land_extent_acres', sa.Numeric(precision=8, scale=2), server_default='1.00', nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('land_preparation_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('seeds_plants_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('fertilizer_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('pesticide_weedicide_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('labor_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('machinery_fuel_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('transport_packaging_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('miscellaneous_cost', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('expected_yield_kg', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), server_default='kg', nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='LKR', nullable=False),
        sa.Column('data_source', sa.String(length=100), server_default='Farmer Reported', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cultivation_budgets_crop_id', 'cultivation_budgets', ['crop_id'])
    op.create_index('ix_cultivation_budgets_district_id', 'cultivation_budgets', ['district_id'])
    op.create_index('ix_cultivation_budgets_year', 'cultivation_budgets', ['year'])
    op.create_index('ix_cultivation_budgets_crop_district_season', 'cultivation_budgets', ['crop_id', 'district_id', 'season', 'year'])

    # 2. Historical Market Prices
    op.create_table(
        'market_prices',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('crop_id', sa.String(length=32), nullable=False),
        sa.Column('market_id', sa.String(length=50), nullable=False),
        sa.Column('market_name', sa.String(length=100), nullable=False),
        sa.Column('district_id', sa.String(length=10), nullable=True),
        sa.Column('price_date', sa.Date(), nullable=False),
        sa.Column('price_type', sa.String(length=20), server_default='wholesale', nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), server_default='kg', nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='LKR', nullable=False),
        sa.Column('volume_traded_kg', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('price_grade', sa.String(length=20), server_default='Standard', nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=False),
        sa.Column('data_quality_flag', sa.String(length=30), server_default='verified', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('crop_id', 'market_id', 'price_date', 'price_type', 'price_grade', name='uq_market_price_entry')
    )
    op.create_index('ix_market_prices_crop_id', 'market_prices', ['crop_id'])
    op.create_index('ix_market_prices_market_id', 'market_prices', ['market_id'])
    op.create_index('ix_market_prices_district_id', 'market_prices', ['district_id'])
    op.create_index('ix_market_prices_price_date', 'market_prices', ['price_date'])
    op.create_index('ix_market_prices_crop_date', 'market_prices', ['crop_id', 'price_date'])
    op.create_index('ix_market_prices_market_date', 'market_prices', ['market_id', 'price_date'])

    # 3. Market Demand Records
    op.create_table(
        'market_demand_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('crop_id', sa.String(length=32), nullable=False),
        sa.Column('district_id', sa.String(length=10), nullable=False),
        sa.Column('market_id', sa.String(length=50), nullable=True),
        sa.Column('period_start_date', sa.Date(), nullable=False),
        sa.Column('period_end_date', sa.Date(), nullable=False),
        sa.Column('demand_volume_kg', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('unit', sa.String(length=20), server_default='kg', nullable=False),
        sa.Column('record_type', sa.String(length=20), nullable=False),
        sa.Column('demand_level', sa.String(length=10), nullable=True),
        sa.Column('confidence_score', sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column('estimation_method', sa.String(length=100), nullable=True),
        sa.Column('is_training_eligible', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('data_source', sa.String(length=100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_demand_records_crop_id', 'market_demand_records', ['crop_id'])
    op.create_index('ix_market_demand_records_district_id', 'market_demand_records', ['district_id'])
    op.create_index('ix_market_demand_records_market_id', 'market_demand_records', ['market_id'])
    op.create_index('ix_market_demand_records_period_start_date', 'market_demand_records', ['period_start_date'])
    op.create_index('ix_market_demand_records_period_end_date', 'market_demand_records', ['period_end_date'])
    op.create_index('ix_market_demand_records_record_type', 'market_demand_records', ['record_type'])
    op.create_index('ix_market_demand_crop_district_date', 'market_demand_records', ['crop_id', 'district_id', 'period_start_date'])
    op.create_index('ix_market_demand_type_eligible', 'market_demand_records', ['record_type', 'is_training_eligible'])

    # 4. Market Profit Analyses (Child table with FK to cultivation_budgets)
    op.create_table(
        'market_profit_analyses',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('analysis_reference', sa.String(length=64), nullable=False),
        sa.Column('crop_id', sa.String(length=32), nullable=False),
        sa.Column('cultivation_district_id', sa.String(length=10), nullable=False),
        sa.Column('target_market_id', sa.String(length=50), nullable=False),
        sa.Column('target_market_name', sa.String(length=100), nullable=True),
        sa.Column('cultivation_budget_id', sa.BigInteger(), nullable=True),
        sa.Column('prediction_status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('forecast_target_date', sa.Date(), nullable=False),
        sa.Column('forecast_horizon_days', sa.Integer(), server_default='90', nullable=False),
        sa.Column('cultivation_extent_acres', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('estimated_production_kg', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('estimated_total_cost', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('forecasted_wholesale_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_confidence_lower', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_confidence_upper', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('projected_demand_volume_kg', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('projected_demand_level', sa.String(length=10), nullable=True),
        sa.Column('projected_revenue', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('projected_net_profit', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('projected_roi_percentage', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('profit_risk_level', sa.String(length=10), nullable=True),
        sa.Column('risk_score', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('risk_factors', sa.JSON(), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('model_provenance', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cultivation_budget_id'], ['cultivation_budgets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_profit_analyses_analysis_reference', 'market_profit_analyses', ['analysis_reference'], unique=True)
    op.create_index('ix_market_profit_analyses_crop_id', 'market_profit_analyses', ['crop_id'])
    op.create_index('ix_market_profit_analyses_cultivation_district_id', 'market_profit_analyses', ['cultivation_district_id'])
    op.create_index('ix_market_profit_analyses_target_market_id', 'market_profit_analyses', ['target_market_id'])
    op.create_index('ix_market_profit_analyses_prediction_status', 'market_profit_analyses', ['prediction_status'])
    op.create_index('ix_market_profit_analyses_profit_risk_level', 'market_profit_analyses', ['profit_risk_level'])
    op.create_index('ix_market_profit_analyses_forecast_target_date', 'market_profit_analyses', ['forecast_target_date'])
    op.create_index('ix_profit_analysis_crop_market_date', 'market_profit_analyses', ['crop_id', 'target_market_id', 'forecast_target_date'])
    op.create_index('ix_profit_analysis_status', 'market_profit_analyses', ['prediction_status', 'profit_risk_level'])


def downgrade() -> None:
    # Drop tables in exact reverse dependency order
    op.drop_table('market_profit_analyses')
    op.drop_table('market_demand_records')
    op.drop_table('market_prices')
    op.drop_table('cultivation_budgets')
