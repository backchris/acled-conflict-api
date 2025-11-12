"""
CSV Import Script for ACLED Conflict API with upsert logic (safe to rerun)
Usage: 
python scripts/import_csv.py data/acled_sample_conflict_data.csv
"""

import sys
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from app.models import ConflictData
from app.config import DevelopmentConfig


def import_csv(csv_path: str):
    """Import conflict data from CSV file"""
    app = create_app(DevelopmentConfig)
    
    with app.app_context():
        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"Error: File not found: {csv_path}")
            sys.exit(1)
        
        imported = 0
        updated = 0
        skipped = 0
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Verify required columns exist
            required = {'country', 'admin1', 'population', 'events', 'score'}
            if not required.issubset(set(reader.fieldnames or [])):
                print(f"Error: Missing required columns: {required}")
                sys.exit(1)
            
            for row in reader:
                try:
                    country = row['country'].strip()
                    admin1 = row['admin1'].strip()
                    events = int(row['events'])
                    score = int(row['score'])
                    
                    # Handle nullable population
                    population = None
                    if row['population'].strip():
                        population = int(row['population'])
                    
                    # Check if record already exists (upsert logic)
                    existing = ConflictData.query.filter_by(
                        country=country,
                        admin1=admin1
                    ).first()
                    
                    if existing:
                        # UPDATE existing record
                        existing.population = population
                        existing.events = events
                        existing.score = score
                        updated += 1
                    else:
                        # INSERT new record
                        record = ConflictData(
                            country=country,
                            admin1=admin1,
                            population=population,
                            events=events,
                            score=score
                        )
                        db.session.add(record)
                        imported += 1
                    
                except (ValueError, KeyError) as e:
                    skipped += 1
                    continue
            
            # Commit all at once
            try:
                db.session.commit()
                print(f"Imported {imported} new records, updated {updated} existing records ({skipped} skipped)")
            except Exception as e:
                db.session.rollback()
                print(f"Error: {e}")
                sys.exit(1)


def main():
    """Parse command-line arguments and run import"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_csv.py <file.csv>")
        sys.exit(1)
    
    import_csv(sys.argv[1])


if __name__ == '__main__':
    main()
