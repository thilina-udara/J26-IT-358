"""Admin panel cultivation planning and concentration analytics routes."""
from typing import Literal, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.schemas.api_responses import error_responses
from app.services.admin_auth import AdminStore, unauthorized_admin, ADMIN_SESSION_PREFIX
from app.services.cultivation_plans import PlanStore


class AdminLoginRequest(BaseModel):
    login_identifier: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=128)


def router(database_path: str, security, historical_predictor=None, production_evidence=None):
    routes = APIRouter(prefix="/api/admin", tags=["admin crop planning portal"])

    def admin_store():
        return AdminStore(database_path)

    def plan_store():
        return PlanStore(database_path)

    def require_officer_or_admin(credentials=Depends(security)):
        if not credentials or credentials.scheme.lower() != "bearer":
            raise unauthorized_admin()
        token = credentials.credentials
        if not token.startswith(ADMIN_SESSION_PREFIX):
            raise unauthorized_admin()
        return admin_store().authenticate(token)

    @routes.get('/analytics/historical-trend/options')
    def historical_trend_options(officer=Depends(require_officer_or_admin)):
        from app.services.historical_trend import options
        return {'series': options()}

    @routes.get('/analytics/historical-trend')
    def historical_trend(
        district: Literal['Matara', 'Hambantota'] = 'Hambantota',
        crop: Literal['Mung Beans', 'Corn', 'Bandakka', 'Brinjal', 'Pumpkin', 'Chillies'] = 'Bandakka',
        season: Literal['Maha', 'Yala'] = 'Maha',
        evaluation_year: int | None = Query(None, ge=1900, le=2200),
        officer=Depends(require_officer_or_admin),
    ):
        from app.services.historical_trend import report
        return report(district, crop, season, evaluation_year)

    @routes.post("/auth/login")
    def admin_login(body: AdminLoginRequest, store=Depends(admin_store)):
        return store.login(body.login_identifier, body.password)

    @routes.get('/analytics/production-forecast/options')
    def production_forecast_options(officer=Depends(require_officer_or_admin)):
        from app.services.production_forecast import options
        return {'series': options(), 'forecast_year': 2026}

    @routes.get('/analytics/production-forecast')
    def production_forecast(
        district: Literal['Matara', 'Hambantota'] = 'Hambantota',
        crop: Literal['Mung Beans', 'Corn', 'Bandakka', 'Brinjal', 'Pumpkin', 'Chillies'] = 'Bandakka',
        season: Literal['Maha', 'Yala'] = 'Maha',
        forecast_year: int = Query(2026, ge=2026, le=2026),
        officer=Depends(require_officer_or_admin),
    ):
        from app.services.production_forecast import report
        return report(district, crop, season)

    @routes.get('/analytics/production-concentration-indicator/options')
    def production_concentration_indicator_options(officer=Depends(require_officer_or_admin)):
        from app.services.production_concentration_indicator import options
        return {'series': options(), 'forecast_year': 2026}

    @routes.get('/analytics/production-concentration-indicator')
    def production_concentration_indicator(
        district: Literal['Matara', 'Hambantota'] = 'Hambantota',
        crop: Literal['Mung Beans', 'Corn', 'Bandakka', 'Brinjal', 'Pumpkin', 'Chillies'] = 'Bandakka',
        season: Literal['Maha', 'Yala'] = 'Maha',
        officer=Depends(require_officer_or_admin),
    ):
        from app.services.production_concentration_indicator import report
        return report(district, crop, season)

    @routes.get("/auth/me")
    def admin_me(profile=Depends(require_officer_or_admin)):
        return profile

    @routes.post("/auth/logout", status_code=204)
    def admin_logout(credentials=Depends(security), store=Depends(admin_store)):
        if not credentials:
            raise unauthorized_admin()
        store.logout(credentials.credentials)
        return None

    @routes.get("/cultivation-plans")
    def list_all_cultivation_plans(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        status: Optional[Literal["active", "cancelled"]] = None,
        crop: Optional[Literal["Mung Beans", "Corn", "Bandakka", "Brinjal", "Pumpkin", "Chillies"]] = None,
        district: Optional[Literal["Matara", "Hambantota"]] = None,
        search_farmer: Optional[str] = None,
        officer=Depends(require_officer_or_admin),
        store=Depends(plan_store),
    ):
        """List and search all registered farmers' cultivation plans across districts."""
        conditions = []
        values = []

        if status:
            conditions.append("p.status = ?")
            values.append(status)
        if crop:
            conditions.append("p.crop = ?")
            values.append(crop)
        if district:
            conditions.append("p.district = ?")
            values.append(district)
        if search_farmer:
            conditions.append("(fa.login_identifier LIKE ? OR p.farmer_id LIKE ?)")
            term = f"%{search_farmer.strip().lower()}%"
            values.extend([term, term])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with store.connection() as db:
            count_query = f"""
                SELECT COUNT(*) FROM cultivation_plans p
                LEFT JOIN farmer_accounts fa ON p.farmer_id = fa.farmer_id
                {where_clause}
            """
            total = db.execute(count_query, values).fetchone()[0]

            data_query = f"""
                SELECT
                    p.plan_id, p.farmer_id, fa.login_identifier as farmer_username,
                    p.district, p.region, p.crop, p.land_size_acres,
                    p.planting_date, p.expected_harvest_date,
                    p.submitted_at, p.updated_at, p.status, p.farmer_declared_season
                FROM cultivation_plans p
                LEFT JOIN farmer_accounts fa ON p.farmer_id = fa.farmer_id
                {where_clause}
                ORDER BY p.submitted_at DESC, p.plan_id DESC
                LIMIT ? OFFSET ?
            """
            rows = db.execute(data_query, [*values, limit, offset]).fetchall()

        items = [dict(r) for r in rows]
        has_more = (offset + len(items)) < total
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": (offset + limit) if has_more else None,
        }

    @routes.get("/analytics/overview")
    def get_analytics_overview(
        officer=Depends(require_officer_or_admin),
        store=Depends(plan_store),
    ):
        """Aggregate statistics: farmer counts, crop distribution, acreage, district trends, and harvest timeline."""
        with store.connection() as db:
            # 1. Total Farmers
            total_farmers_res = db.execute("SELECT COUNT(*) FROM farmer_accounts").fetchone()
            total_farmers = total_farmers_res[0] if total_farmers_res else 0

            # 2. Total Plans & Active Plans
            plan_counts = db.execute("""
                SELECT
                    COUNT(*) as total_plans,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_plans,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_plans,
                    COALESCE(SUM(CASE WHEN status = 'active' THEN land_size_acres ELSE 0 END), 0) as total_active_acreage
                FROM cultivation_plans
            """).fetchone()

            # 3. Crop Distribution (Acreage & Count)
            crop_distribution = db.execute("""
                SELECT
                    crop,
                    COUNT(*) as plan_count,
                    COALESCE(SUM(land_size_acres), 0) as total_acres
                FROM cultivation_plans
                WHERE status = 'active'
                GROUP BY crop
                ORDER BY total_acres DESC
            """).fetchall()

            # 4. District & Season breakdown
            district_summary = db.execute("""
                SELECT
                    district,
                    crop,
                    COUNT(*) as plan_count,
                    COALESCE(SUM(land_size_acres), 0) as total_acres
                FROM cultivation_plans
                WHERE status = 'active'
                GROUP BY district, crop
                ORDER BY district, total_acres DESC
            """).fetchall()

            # 5. Harvest timeline distribution by month
            harvest_timeline = db.execute("""
                SELECT
                    substr(expected_harvest_date, 1, 7) as harvest_month,
                    crop,
                    COUNT(*) as plan_count,
                    COALESCE(SUM(land_size_acres), 0) as total_acres
                FROM cultivation_plans
                WHERE status = 'active'
                GROUP BY harvest_month, crop
                ORDER BY harvest_month ASC
            """).fetchall()

            # 6. Recent plan registrations
            recent_plans = db.execute("""
                SELECT
                    p.plan_id, fa.login_identifier as farmer_username,
                    p.crop, p.district, p.region, p.land_size_acres,
                    p.planting_date, p.expected_harvest_date, p.submitted_at, p.status
                FROM cultivation_plans p
                LEFT JOIN farmer_accounts fa ON p.farmer_id = fa.farmer_id
                ORDER BY p.submitted_at DESC
                LIMIT 10
            """).fetchall()

        return {
            "summary": {
                "total_farmers": total_farmers,
                "total_plans": plan_counts["total_plans"] if plan_counts else 0,
                "active_plans": plan_counts["active_plans"] if plan_counts else 0,
                "cancelled_plans": plan_counts["cancelled_plans"] if plan_counts else 0,
                "total_active_acreage": round(plan_counts["total_active_acreage"], 2) if plan_counts else 0,
            },
            "crop_distribution": [dict(r) for r in crop_distribution],
            "district_summary": [dict(r) for r in district_summary],
            "harvest_timeline": [dict(r) for r in harvest_timeline],
            "recent_plans": [dict(r) for r in recent_plans],
        }

    @routes.get("/analytics/ml-research-monitoring")
    def get_ml_research_monitoring(
        district: Optional[Literal["Matara", "Hambantota"]] = None,
        mode: Literal["live", "synthetic_demo"] = Query("live"),
        officer=Depends(require_officer_or_admin),
        store=Depends(plan_store),
    ):
        """XGBoost model benchmark status and DBSCAN/K-Means cluster risk proxy monitoring.
        
        Explicitly flags and documents research proxy metrics vs. operational risk.
        Supports 'live' operational snapshot or isolated 'synthetic_demo' cohort demonstration.
        """
        from app.services.plan_clustering import snapshot, analyze
        from app.services.research_metadata import BENCHMARKS

        now = datetime.now(timezone.utc)
        current_snapshot = snapshot(store, now) if mode == "live" else []

        clustering_results = {}
        target_districts = [district] if district else ["Matara", "Hambantota"]

        if mode == "synthetic_demo":
            from app.services.synthetic_clustering_demo import run_synthetic_research_clustering
            for dist in target_districts:
                try:
                    clustering_results[dist] = run_synthetic_research_clustering(dist)
                except Exception as e:
                    clustering_results[dist] = {"error": str(e), "kmeans": [], "dbscan": [], "noise": {}}
        else:
            for dist in target_districts:
                try:
                    clustering_results[dist] = analyze(
                        current_snapshot,
                        district=dist,
                        clusters=3,
                        eps=1.0,
                        min_samples=2,
                    )
                    clustering_results[dist]["mode"] = "live_operational"
                except Exception as e:
                    clustering_results[dist] = {"error": str(e), "kmeans": [], "dbscan": [], "noise": {}}

        from app.services.model_validation_metrics import load_frozen_validation_metrics

        try:
            validation_metrics = load_frozen_validation_metrics()
        except Exception as e:
            validation_metrics = {"error": f"Failed to load frozen validation metrics: {str(e)}"}

        return {
            "disclaimer": "RESEARCH PROXY OUTPUT: Concentration indices, DBSCAN/K-Means clusters, and XGBoost estimations are analytical research proxies developed for regional crop pattern evaluation, not certified financial or yield guarantees.",
            "benchmarks": BENCHMARKS,
            "clustering": clustering_results,
            "validation_metrics": validation_metrics,
            "active_plan_count_evaluated": len(current_snapshot),
            "generated_at": now.isoformat(),
        }

    return routes
