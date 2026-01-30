"""
Command-line interface for database management.
"""
import os
import sys
import click
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from alembic import command
from alembic.config import Config
import json
import numpy as np

from job_application_automation.src.database import init_db, get_engine, check_database_connection, get_database_stats
from job_application_automation.src.models import Base, JobApplication, JobSkill, SearchHistory, VectorIndex
from job_application_automation.src.vector_database import vector_db, VectorDatabaseService
from job_application_automation.src.database_monitor import DatabaseMonitorService, vector_monitor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """Database management command-line interface."""
    pass

@cli.command()
def init():
    """Initialize database and create tables."""
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        sys.exit(1)

@cli.command()
def check():
    """Check database connection and health."""
    try:
        logger.info("Checking database connection...")
        success, error = check_database_connection()
        if success:
            logger.info("Database connection successful")
            stats = get_database_stats()
            logger.info("Database statistics:")
            logger.info(f"Status: {stats['status']}")
            logger.info("Connection pool:")
            for key, value in stats["connection_pool"].items():
                logger.info(f"  {key}: {value}")
            logger.info("Tables:")
            for table, data in stats["tables"].items():
                logger.info(f"  {table}: {data['row_count']} rows")
        else:
            logger.error(f"Database connection failed: {error}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error checking database: {e}")
        sys.exit(1)

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
def make_migration(message):
    """Create a new database migration."""
    try:
        logger.info(f"Creating migration: {message}")
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Create migration
        command.revision(alembic_cfg,
                        message=message,
                        autogenerate=True)
        
        logger.info("Migration created successfully")
    except Exception as e:
        logger.error(f"Error creating migration: {e}")
        sys.exit(1)

@cli.command()
@click.option('--revision', '-r', default='head',
              help='Revision to upgrade to (default: head)')
def upgrade(revision):
    """Upgrade database to a later version."""
    try:
        logger.info(f"Upgrading database to revision: {revision}")
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Run upgrade
        command.upgrade(alembic_cfg, revision)
        
        logger.info("Database upgraded successfully")
    except Exception as e:
        logger.error(f"Error upgrading database: {e}")
        sys.exit(1)

@cli.command()
@click.option('--revision', '-r', required=True,
              help='Revision to downgrade to')
def downgrade(revision):
    """Downgrade database to a previous version."""
    try:
        logger.info(f"Downgrading database to revision: {revision}")
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Run downgrade
        command.downgrade(alembic_cfg, revision)
        
        logger.info("Database downgraded successfully")
    except Exception as e:
        logger.error(f"Error downgrading database: {e}")
        sys.exit(1)

@cli.command()
def history():
    """Show database migration history."""
    try:
        logger.info("Getting migration history...")
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Show history
        command.history(alembic_cfg)
    except Exception as e:
        logger.error(f"Error getting migration history: {e}")
        sys.exit(1)

@cli.command()
@click.option('--output', '-o', default='backup.sql',
              help='Output file name (default: backup.sql)')
def backup(output):
    """Backup database to a file."""
    try:
        logger.info(f"Backing up database to: {output}")
        
        engine = get_engine()
        if str(engine.url).startswith('sqlite'):
            # For SQLite, we can just copy the database file
            import shutil
            db_path = str(engine.url).replace('sqlite:///', '')
            backup_path = f"{db_path}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
        else:
            # For other databases, implement appropriate backup logic
            logger.error("Backup not implemented for this database type")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error backing up database: {e}")
        sys.exit(1)

@cli.command()
def current():
    """Show current database revision."""
    try:
        logger.info("Getting current revision...")
        
        # Get alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Show current revision
        command.current(alembic_cfg)
    except Exception as e:
        logger.error(f"Error getting current revision: {e}")
        sys.exit(1)

@cli.command()
@click.confirmation_option(prompt='Are you sure you want to reset the database?')
def reset():
    """Reset database (WARNING: This will delete all data)."""
    try:
        logger.warning("Resetting database...")
        
        # Drop all tables
        engine = get_engine()
        Base.metadata.drop_all(engine)
        
        # Recreate tables
        Base.metadata.create_all(engine)
        
        logger.info("Database reset successfully")
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        sys.exit(1)

@cli.group()
def monitor():
    """Monitor database health and performance."""
    pass

@monitor.command()
def health():
    """Check current database health."""
    try:
        logger.info("Checking database health...")
        from job_application_automation.src.database import get_engine
        from job_application_automation.src.database_monitor import DatabaseMonitorService
        
        monitor_service = DatabaseMonitorService(get_engine())
        import asyncio
        health_check = asyncio.run(monitor_service.check_database_health())
        
        if health_check["status"] == "healthy":
            logger.info("Database health check passed")
            logger.info("Connection pool stats:")
            for key, value in health_check["connection_pool"].items():
                logger.info(f"  {key}: {value}")
            
            if health_check.get("alerts"):
                logger.warning("Alerts found:")
                for alert in health_check["alerts"]:
                    logger.warning(f"  {alert['level']}: {alert['message']}")
                    
            if health_check.get("recommendations"):
                logger.info("Recommendations:")
                for rec in health_check["recommendations"]:
                    logger.info(f"  {rec['type']}: {rec['message']}")
        else:
            logger.error(f"Database health check failed: {health_check.get('error')}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error checking database health: {e}")
        sys.exit(1)

@monitor.command()
@click.option('--days', '-d', default=1, help='Number of days to analyze')
def slow_queries(days):
    """Show slow query report."""
    try:
        logger.info(f"Generating slow query report for the last {days} days...")
        from job_application_automation.src.database import get_engine
        from job_application_automation.src.database_monitor import DatabaseMonitorService
        
        monitor_service = DatabaseMonitorService(get_engine())
        report = monitor_service.get_slow_query_report(days)
        
        logger.info(f"Found {report['total_slow_queries']} slow queries")
        if report['queries']:
            logger.info("Top slow queries:")
            for query in report['queries']:
                logger.info(f"\nQuery: {query['query']}")
                logger.info(f"Average time: {query['stats']['avg_time']:.2f}s")
                logger.info(f"Executions: {query['stats']['count']}")
                logger.info(f"Total time: {query['stats']['total_time']:.2f}s")
        
        logger.info("\nSummary:")
        logger.info(f"Total slow query time: {report['summary']['total_time']:.2f}s")
        logger.info(f"Average query time: {report['summary']['avg_time']:.2f}s")
    except Exception as e:
        logger.error(f"Error generating slow query report: {e}")
        sys.exit(1)

@monitor.command()
def performance():
    """Show current database performance metrics."""
    try:
        logger.info("Getting database performance metrics...")
        from job_application_automation.src.database import get_engine
        from job_application_automation.src.database_monitor import DatabaseMonitorService
        
        monitor_service = DatabaseMonitorService(get_engine())
        metrics = monitor_service.get_performance_metrics()
        
        logger.info("\nPerformance Score: {:.1f}/100".format(metrics["performance_score"]))
        
        logger.info("\nQuery Statistics:")
        for key, value in metrics["query_stats"].items():
            if isinstance(value, float):
                logger.info(f"  {key}: {value:.2f}")
            else:
                logger.info(f"  {key}: {value}")
        
        logger.info("\nConnection Pool Status:")
        for key, value in metrics["pool_stats"].items():
            logger.info(f"  {key}: {value}")
            
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        sys.exit(1)

@monitor.command()
def analyze():
    """Analyze query patterns and provide optimization recommendations."""
    try:
        logger.info("Analyzing query patterns...")
        from job_application_automation.src.database import get_engine
        from job_application_automation.src.database_monitor import DatabaseMonitorService, analyze_query_patterns
        
        analysis = analyze_query_patterns()
        
        if analysis["recommendations"]:
            logger.info("\nOptimization Recommendations:")
            for rec in analysis["recommendations"]:
                logger.info(f"\n{rec['type'].upper()}:")
                logger.info(f"  {rec['message']}")
        
        if analysis["peak_times"]:
            logger.info("\nPeak Usage Times:")
            sorted_hours = sorted(
                analysis["peak_times"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for hour, count in sorted_hours[:5]:
                logger.info(f"  {hour:02d}:00 - {count} queries")
    except Exception as e:
        logger.error(f"Error analyzing query patterns: {e}")
        sys.exit(1)

@cli.group()
def vector():
    """Manage FAISS vector database."""
    pass

@vector.command()
@click.argument('index_name')
@click.option('--dimension', '-d', default=384, help='Vector dimension')
@click.option('--type', '-t', default='Flat', 
              type=click.Choice(['Flat', 'HNSW', 'IVF']),
              help='FAISS index type')
@click.option('--entity-type', '-e', default='jobs',
              type=click.Choice(['jobs', 'skills', 'searches']),
              help='Entity type for this index')
def create_index(index_name, dimension, type, entity_type):
    """Create a new FAISS vector index."""
    try:
        logger.info(f"Creating {type} index '{index_name}' with dimension {dimension}")
        success = vector_db.create_index(index_name, dimension, type)
        
        if success:
            # Store index information in SQL database
            from sqlalchemy.orm import Session
            from job_application_automation.src.database import get_db
            
            with get_db() as db:
                index_record = VectorIndex(
                    index_name=index_name,
                    entity_type=entity_type,
                    dimension=dimension,
                    index_type=type,
                    item_count=0,
                    index_path=str(vector_db.index_dir / f"{index_name}.index")
                )
                db.add(index_record)
                db.commit()
                
            logger.info(f"Successfully created index '{index_name}'")
        else:
            logger.error(f"Failed to create index '{index_name}'")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error creating index: {e}")
        sys.exit(1)

@vector.command()
@click.argument('index_name')
def delete_index(index_name):
    """Delete a FAISS vector index."""
    try:
        logger.info(f"Deleting index '{index_name}'")
        success = vector_db.delete_index(index_name)
        
        if success:
            # Remove index from SQL database
            from sqlalchemy.orm import Session
            from job_application_automation.src.database import get_db
            
            with get_db() as db:
                index_record = db.query(VectorIndex).filter_by(index_name=index_name).first()
                if index_record:
                    db.delete(index_record)
                    db.commit()
                    
            logger.info(f"Successfully deleted index '{index_name}'")
        else:
            logger.error(f"Failed to delete index '{index_name}'")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error deleting index: {e}")
        sys.exit(1)

@vector.command()
def list_indices():
    """List all FAISS vector indices."""
    try:
        logger.info("Listing vector indices")
        from job_application_automation.src.database import get_db
        
        # Get indices from SQL database
        with get_db() as db:
            indices = db.query(VectorIndex).all()
            
        if indices:
            logger.info(f"Found {len(indices)} vector indices:")
            for idx in indices:
                logger.info(f"  {idx.index_name} - Type: {idx.index_type}, "
                          f"Dimension: {idx.dimension}, Items: {idx.item_count}, "
                          f"Entity: {idx.entity_type}")
        else:
            logger.info("No vector indices found")
            
        # Get FAISS index stats
        stats = vector_db.get_index_stats()
        if stats:
            logger.info("\nFAISS index statistics:")
            for name, data in stats.items():
                logger.info(f"  {name}: {data['item_count']} items, "
                          f"created: {data['created_at']}")
        
    except Exception as e:
        logger.error(f"Error listing indices: {e}")
        sys.exit(1)

@vector.command()
@click.argument('index_name')
@click.option('--jobs', '-j', is_flag=True, help='Index job applications')
@click.option('--skills', '-s', is_flag=True, help='Index job skills')
@click.option('--searches', '-q', is_flag=True, help='Index search history')
@click.option('--rebuild', '-r', is_flag=True, help='Rebuild index from scratch')
def build_index(index_name, jobs, skills, searches, rebuild):
    """Build or update a FAISS vector index from database records."""
    try:
        if not any([jobs, skills, searches]):
            logger.error("Specify at least one entity type to index (--jobs, --skills, --searches)")
            sys.exit(1)
            
        # Check if index exists, create if not
        stats = vector_db.get_index_stats(index_name)
        if not stats and not rebuild:
            logger.error(f"Index '{index_name}' does not exist. Create it first or use --rebuild")
            sys.exit(1)
            
        from job_application_automation.src.database import get_db
        
        if jobs:
            logger.info(f"Indexing job applications in '{index_name}'")
            with get_db() as db:
                # Get job applications
                applications = db.query(JobApplication).all()
                if not applications:
                    logger.info("No job applications found to index")
                else:
                    # Prepare items for indexing
                    items = []
                    for app in applications:
                        text = f"{app.job_title} {app.company} "
                        if app.job_description:
                            text += app.job_description
                        items.append({
                            "id": app.id,
                            "text": text
                        })
                    
                    # Create index if using rebuild
                    if rebuild:
                        vector_db.create_index(index_name, 384, "Flat")
                        
                    # Add items to index
                    vector_db.add_items(index_name, items, text_field="text", id_field="id")
                    logger.info(f"Indexed {len(items)} job applications")
                    
                    # Update index record
                    index_record = db.query(VectorIndex).filter_by(index_name=index_name).first()
                    if index_record:
                        index_record.item_count = len(items)
                        index_record.updated_at = datetime.utcnow()
                        db.commit()
        
        if skills:
            logger.info(f"Indexing job skills in '{index_name}'")
            with get_db() as db:
                # Get job skills
                skills = db.query(JobSkill).all()
                if not skills:
                    logger.info("No job skills found to index")
                else:
                    # Prepare items for indexing
                    items = []
                    for skill in skills:
                        text = f"{skill.skill_name} {skill.skill_category}"
                        items.append({
                            "id": skill.id,
                            "text": text
                        })
                    
                    # Create index if using rebuild
                    if rebuild:
                        vector_db.create_index(index_name, 384, "Flat")
                        
                    # Add items to index
                    vector_db.add_items(index_name, items, text_field="text", id_field="id")
                    logger.info(f"Indexed {len(items)} job skills")
                    
                    # Update index record
                    index_record = db.query(VectorIndex).filter_by(index_name=index_name).first()
                    if index_record:
                        index_record.item_count = len(items)
                        index_record.updated_at = datetime.utcnow()
                        db.commit()
        
        if searches:
            logger.info(f"Indexing search history in '{index_name}'")
            with get_db() as db:
                # Get search history
                searches = db.query(SearchHistory).all()
                if not searches:
                    logger.info("No search history found to index")
                else:
                    # Prepare items for indexing
                    items = []
                    for search in searches:
                        text = f"{search.keywords} {search.location}"
                        items.append({
                            "id": search.id,
                            "text": text
                        })
                    
                    # Create index if using rebuild
                    if rebuild:
                        vector_db.create_index(index_name, 384, "Flat")
                        
                    # Add items to index
                    vector_db.add_items(index_name, items, text_field="text", id_field="id")
                    logger.info(f"Indexed {len(items)} search history items")
                    
                    # Update index record
                    index_record = db.query(VectorIndex).filter_by(index_name=index_name).first()
                    if index_record:
                        index_record.item_count = len(items)
                        index_record.updated_at = datetime.utcnow()
                        db.commit()
    
    except Exception as e:
        logger.error(f"Error building index: {e}")
        sys.exit(1)

@vector.command()
@click.argument('index_name')
@click.argument('query')
@click.option('--limit', '-l', default=10, help='Maximum number of results')
@click.option('--entity-type', '-e', type=click.Choice(['jobs', 'skills', 'searches']),
             help='Entity type to retrieve')
def search(index_name, query, limit, entity_type):
    """Search a FAISS vector index."""
    try:
        logger.info(f"Searching '{index_name}' for: {query}")
        
        # Perform search
        results = vector_db.search(index_name, query, k=limit)
        
        if not results:
            logger.info("No results found")
            return
            
        logger.info(f"Found {len(results)} results:")
        
        from job_application_automation.src.database import get_db
        
        with get_db() as db:
            # Get entity type from index if not specified
            if not entity_type:
                index_record = db.query(VectorIndex).filter_by(index_name=index_name).first()
                if index_record:
                    entity_type = index_record.entity_type
                else:
                    entity_type = 'jobs'  # default
            
            # Fetch full records based on IDs
            for idx, (item_id, distance) in enumerate(results):
                if entity_type == 'jobs':
                    record = db.query(JobApplication).filter_by(id=item_id).first()
                    if record:
                        logger.info(f"  {idx+1}. [{distance:.4f}] {record.job_title} at {record.company}")
                elif entity_type == 'skills':
                    record = db.query(JobSkill).filter_by(id=item_id).first()
                    if record:
                        logger.info(f"  {idx+1}. [{distance:.4f}] {record.skill_name} ({record.skill_category})")
                elif entity_type == 'searches':
                    record = db.query(SearchHistory).filter_by(id=item_id).first()
                    if record:
                        logger.info(f"  {idx+1}. [{distance:.4f}] {record.keywords} in {record.location}")
                else:
                    logger.info(f"  {idx+1}. [{distance:.4f}] ID: {item_id}")
    
    except Exception as e:
        logger.error(f"Error searching index: {e}")
        sys.exit(1)

@vector.command()
def stats():
    """Show vector database performance statistics."""
    try:
        from job_application_automation.src.database_monitor import DatabaseMonitorService, vector_monitor
        from job_application_automation.src.database import get_engine
        
        monitor_service = DatabaseMonitorService(get_engine())
        stats = monitor_service.get_vector_db_metrics()
        
        if stats["total_operations"] == 0:
            logger.info("No vector operations recorded yet")
            return
        
        logger.info(f"Vector Database Statistics:")
        logger.info(f"  Total Operations: {stats['total_operations']}")
        logger.info(f"  Total Time: {stats['total_time']:.2f}s")
        logger.info(f"  Average Time per Operation: {stats['avg_time_per_op']:.4f}s")
        logger.info(f"  Success Rate: {stats['success_rate']:.1f}%")
        logger.info(f"  Total Vectors Processed: {stats['total_vectors_processed']}")
        
        if stats["operations_by_type"]:
            logger.info("\nOperations by Type:")
            for op_type, op_stats in stats["operations_by_type"].items():
                logger.info(f"  {op_type}: {op_stats['count']} ops, "
                          f"avg {op_stats['avg_time']:.4f}s")
        
        if stats["operations_by_index"]:
            logger.info("\nOperations by Index:")
            for index, idx_stats in stats["operations_by_index"].items():
                logger.info(f"  {index}: {idx_stats['count']} ops, "
                          f"avg {idx_stats['avg_time']:.4f}s")
        
        if stats["slow_operations"]:
            logger.info("\nSlow Operations:")
            for op in stats["slow_operations"]:
                logger.info(f"  {op['operation']} on {op['index_name']}: "
                          f"avg {op['avg_time']:.4f}s ({op['count']} ops)")
    
    except Exception as e:
        logger.error(f"Error getting vector statistics: {e}")
        sys.exit(1)

@vector.command()
@click.option('--format', '-f', default='json', type=click.Choice(['json', 'csv']), 
             help='Output format')
@click.option('--output', '-o', default='metrics', help='Output directory')
def export_stats(format, output):
    """Export vector database statistics to file."""
    try:
        from job_application_automation.src.database import get_engine
        from job_application_automation.src.database_monitor import DatabaseMonitorService
        
        monitor_service = DatabaseMonitorService(get_engine())
        filepath = monitor_service.export_vector_metrics(format=format, output_dir=output)
        
        logger.info(f"Vector database statistics exported to: {filepath}")
    
    except Exception as e:
        logger.error(f"Error exporting vector statistics: {e}")
        sys.exit(1)

@vector.command()
def clear_stats():
    """Reset vector database performance statistics."""
    try:
        vector_monitor.reset_stats()
        logger.info("Vector database statistics reset successfully")
    
    except Exception as e:
        logger.error(f"Error resetting vector statistics: {e}")
        sys.exit(1)

if __name__ == '__main__':
    cli()