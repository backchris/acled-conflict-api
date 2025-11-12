"""Conflict data routes - for getting and managing conflict data"""
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import NotFound
from app.models import ConflictData
from app.schemas import ConflictDataRow, ConflictDataListResponse, CountryDataResponse


conflict_bp = Blueprint('conflict', __name__, url_prefix='')

@conflict_bp.route('', methods=['GET'])
def get_all_conflicts():
    """
    List conflict data for each country with pagination 
    (default to returning 20 countries per page). 
    Note that this will result in multiple entries per country 
    since each country can have multiple admin1 entries.
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

@conflict_bp.route('/<countries>', methods=['GET'])
def get_country_conflicts(countries):
    """
    Based on country name, list country-admin1 details, 
    including the admin1 names, conflict risk scores, and population per admin1. 
    Allow for multiple country names to be accepted.
    """
    try:
        # 1. Split countries by comma and strip whitespace
        country_list = [c.strip() for c in countries.split(',')]
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
    


    

