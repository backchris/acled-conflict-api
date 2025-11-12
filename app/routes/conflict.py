"""Conflict data routes - for getting and managing conflict data"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from werkzeug.exceptions import NotFound, BadRequest
from datetime import datetime, timezone
from app.models import ConflictData, RiskCache, Feedback, User
from app.schemas import (
    ConflictDataRow, ConflictDataListResponse, CountryDataResponse, 
    RiskScoreResponse, FeedbackCreateRequest, FeedbackResponse,
    DeleteRequest, DeleteResponse
)
from app.extensions import db
from app.auth_utils import require_admin


conflict_bp = Blueprint('conflict', __name__, url_prefix='')

@conflict_bp.route('', methods=['GET'])
def get_all_conflicts():
    """
    List conflict data for each country with pagination 
    (default to returning 20 countries per page). 
    Note that this will result in multiple entries per country 
    since each country can have multiple admin1 entries.
    Request:
    - URL Params: page (int, default 1), per_page (int, default 20 and max 100)
    Response:
    - 200: ConflictDataListResponse with paginated conflict data
    - 400: Invalid pagination parameters
    - 500: Internal server error
    """
    try:
        # 1. Get pagination params from query string
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if page < 1 or per_page < 1 or per_page > 100:
            raise ValueError("Invalid pagination parameters provided from URL")
        
        # 2. Query DB with pagination
        paginated_data = ConflictData.query.order_by(
            ConflictData.country, ConflictData.admin1
        ).paginate(page=page, per_page=per_page, error_out=False)

        # 3. Convert to ConflictData row schema
        rows = [ConflictDataRow.model_validate(row) for row in paginated_data.items]

        # 4. Build response schema
        response = ConflictDataListResponse(
            page=page,
            per_page=per_page,
            total=paginated_data.total,
            data=rows
        )
        return jsonify(response.model_dump()), 200
    
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@conflict_bp.route('/<country>', methods=['GET'])
def get_country_conflicts(country):
    """
    Based on country name, list country-admin1 details, 
    including the admin1 names, conflict risk scores, and population per admin1. 
    Allow for multiple country names to be accepted.
    Request:
    - URL Param: country (single or comma separated list of country names)
    Response:
    - 200: CountryDataResponse single or list of multiple countries
    - 400: Invalid request (ie. no valid country names)
    - 404: No conflict data found for provided countries
    - 500: Internal server error
    """
    try:
        # 1. Split countries by comma and strip whitespace
        country_list = [c.strip() for c in country.split(',')]
        if not country_list:
            raise ValueError("No valid country names provided in URL")
        
        # 2. Query DB for all matching countries
        query = ConflictData.query.filter(
            ConflictData.country.in_(country_list)
        ).order_by(ConflictData.country, ConflictData.admin1)

        conflict_rows = query.all()

        if not conflict_rows:
            raise NotFound("No conflict data found for provided countries")

        # 3. Group returned data by country in dictionary that maps country name to list of ConflictDataRow Pydantic models of each row
        country_dict = {}
        for row in conflict_rows:
            country_name = row.country
            if country_name not in country_dict:
                country_dict[country_name] = []
            country_dict[country_name].append(ConflictDataRow.model_validate(row))
        
        # 4. Build response list, return single object if one country, else list of objects
        if len(country_list) == 1:
            response = CountryDataResponse(
                country=country_list[0],
                admin1_entries=country_dict.get(country_list[0], [])
            )
            return jsonify(response.model_dump()), 200
        else:
            responses = [
                CountryDataResponse(country=c, admin1_entries=country_dict.get(c, []))
                for c in country_list
            ]
            return jsonify([r.model_dump() for r in responses]), 200
    
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except NotFound as nf:
        return jsonify({'error': str(nf)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
    
@conflict_bp.route('/<country>/riskscore', methods=['GET'])
def get_country_riskscore(country):
    """
    Return the average risk score for the country using a background job 
    to average the risk scores across admin1’s for the country
    
    Strategy: Cache results using RiskCache table for performance
    - First request: Compute average sync + cache it
    - Subsequent requests: Return cached average instantly
    
    Response:
    - 200: Returns RiskScoreResponse with avg_score (cached or freshly computed)
    - 404: Country not found
    - 500: Internal server error
    """
    try:
        # 1. Check country exists in ConflictData
        exists = db.session.query(
            func.count(ConflictData.id)
        ).filter(ConflictData.country == country).scalar()

        if not exists:
            raise NotFound(f"No conflict data found for country: {country}")
        
        # 2. Check RiskCache for pre-computed average
        risk_cache = RiskCache.query.filter_by(country=country).first()
        
        if risk_cache:
            # Cache hit! Return cached result instantly
            response = RiskScoreResponse.model_validate(risk_cache)
            return jsonify(response.model_dump()), 200
        
        # 3. Cache miss - Compute average synchronously on first request
        # This queries all admin1 scores for the country and computes average
        avg_score = db.session.query(
            func.avg(ConflictData.score)
        ).filter(ConflictData.country == country).scalar()
        
        # Handle case where country has no data (shouldn't happen given check above)
        if avg_score is None:
            avg_score = 0.0
        else:
            avg_score = float(avg_score)
        
        # 4. Store in cache for subsequent requests
        risk_cache = RiskCache(
            country=country,
            avg_score=avg_score,
            computed_at=datetime.now(timezone.utc)
        )
        db.session.add(risk_cache)
        db.session.commit()
        
        # 5. Return computed result
        response = RiskScoreResponse.model_validate(risk_cache)
        return jsonify(response.model_dump()), 200
    
    except NotFound as nf:
        return jsonify({'error': str(nf)}), 404
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@conflict_bp.route('/<admin1>/userfeedback', methods=['POST'])
@jwt_required()
def post_user_feedback(admin1):
    """
    Add user feedback about the admin1 (authentication required)
    User feedback text must be at least 10 characters but no more than 500 characters
    Request:
    - Body: FeedbackCreateRequest (text of 10-500 chars)
    - Header: Authorization: Bearer

    Response:
    - 201: Feedback created successfully
    - 400: Invalid request
    - 404: Admin1 region not found
    - 500: Internal server error, Database error
    """
    try:
        # 1. Get user_id from JWT token
        user_id = get_jwt_identity()
        
        # 2. Parse request body
        try:
            req_data = FeedbackCreateRequest(**request.get_json() or {})
        except Exception as e:
            raise BadRequest(f'Invalid request: {str(e)}')
        
        # 3. Find ConflictData record by admin1
        conflict = ConflictData.query.filter_by(admin1=admin1).first()
        if not conflict:
            raise NotFound(f"Admin1 region not found: {admin1}")
        
        # 4. Create Feedback record
        feedback = Feedback(
            user_id=int(user_id),  # user_id from JWT is string - convert to int
            conflict_id=conflict.id,
            country=conflict.country,
            admin1=admin1,
            text=req_data.text
        )
        
        # 5. Save to database
        try:
            db.session.add(feedback)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        
        # 6. Return created feedback
        response = FeedbackResponse.model_validate(feedback)
        return jsonify(response.model_dump()), 201

    except BadRequest as br:
        return jsonify({'error': str(br)}), 400
    except NotFound as nf:
        return jsonify({'error': str(nf)}), 404
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@conflict_bp.route('', methods=['DELETE'])
@jwt_required()
@require_admin
def delete_conflict_data():
    """
    Delete conflict data records (admin only).
    Allow admin user to delete entries from the table based on admin1 and country combination
    
    Request:
    - Body: DeleteRequest (country, admin1)
    - Header: Authorization : Bearer (admin JWT token)
    
    Response:
    - 200: Records deleted successfully
    - 400: Invalid request
    - 404: No matching records found
    - 403: Not authorized (not admin)
    - 500: Internal server error, Database error
    """
    try:
        # 1. Parse request body
        try:
            req_data = DeleteRequest(**request.get_json() or {})
        except Exception as e:
            return jsonify({'error': f'Invalid request: {str(e)}'}), 400
        
        # 2. Delete matching records
        deleted_count = ConflictData.query.filter_by(
            country=req_data.country,
            admin1=req_data.admin1
        ).delete()
        
        if deleted_count == 0:
            raise NotFound(f"No records found for {req_data.country}/{req_data.admin1}")
        
        # 3. Commit deletion
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        
        # 4. Return result
        response = DeleteResponse(deleted=deleted_count)
        return jsonify(response.model_dump()), 200
    
    except NotFound as nf:
        return jsonify({'error': str(nf)}), 404
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
