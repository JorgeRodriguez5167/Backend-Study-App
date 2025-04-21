#!/usr/bin/env python3
"""
MySQL Connection Test Script

This script tests the connection to the MySQL database using the credentials
from environment variables or provided as command-line arguments.
"""

import os
import sys
import logging
import argparse
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mysql_test")

def test_mysql_connection(host, port, user, password, database):
    """Test connection to MySQL database"""
    try:
        # Create connection string
        connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        logger.info(f"Testing connection to MySQL at {host}:{port}/{database}")
        
        # Create engine
        engine = create_engine(connection_string)
        
        # Test connection with a simple query
        with engine.connect() as conn:
            logger.info("Connection established successfully!")
            
            # Check if we can execute a query
            result = conn.execute(text("SELECT VERSION()"))
            version = result.scalar()
            logger.info(f"MySQL version: {version}")
            
            # Get database tables
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema = '{database}'"
            ))
            tables = [row[0] for row in result]
            
            if tables:
                logger.info(f"Available tables: {', '.join(tables)}")
            else:
                logger.info("No tables found in the database")
                
        return True
    
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        return False

def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Test MySQL connection")
    
    parser.add_argument("--host", default=os.environ.get("MYSQLHOST", "mysql.railway.internal"), help="MySQL host")
    parser.add_argument("--port", default=os.environ.get("MYSQLPORT", "3306"), help="MySQL port")
    parser.add_argument("--user", default=os.environ.get("MYSQLUSER", "root"), help="MySQL username")
    parser.add_argument("--password", default=os.environ.get("MYSQLPASSWORD", ""), help="MySQL password")
    parser.add_argument("--database", default=os.environ.get("MYSQLDATABASE", "railway"), help="MySQL database name")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    logger.info("Starting MySQL connection test")
    success = test_mysql_connection(
        args.host,
        args.port,
        args.user,
        args.password,
        args.database
    )
    
    sys.exit(0 if success else 1) 