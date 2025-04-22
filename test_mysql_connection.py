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
from datetime import date

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
                
                # Test user table columns
                if 'user' in tables:
                    result = conn.execute(text(
                        "SHOW COLUMNS FROM user"
                    ))
                    columns = [row[0] for row in result]
                    logger.info(f"User table columns: {', '.join(columns)}")
                    
                    # Check if date_of_birth column exists
                    if 'date_of_birth' in columns:
                        logger.info("date_of_birth column exists in user table")
                    else:
                        logger.warning("date_of_birth column does not exist in user table")
                
                # Test creating a sample user with date_of_birth
                if 'user' in tables:
                    # First, delete any test user that might exist
                    conn.execute(text("DELETE FROM user WHERE username = 'testuser'"))
                    
                    # Create a test user with date_of_birth
                    today = date.today().isoformat()
                    conn.execute(text(
                        f"""INSERT INTO user (username, password, email, first_name, last_name, age, date_of_birth, major, created_at) 
                        VALUES ('testuser', 'password123', 'test@example.com', 'Test', 'User', 25, '{today}', 'Computer Science', NOW())"""
                    ))
                    logger.info("Successfully created test user with date_of_birth")
                    
                    # Read back the user to verify
                    result = conn.execute(text("SELECT * FROM user WHERE username = 'testuser'"))
                    user = result.fetchone()
                    if user:
                        logger.info(f"Retrieved test user: {user}")
                    else:
                        logger.warning("Failed to retrieve test user")
                    
                    # Clean up
                    conn.execute(text("DELETE FROM user WHERE username = 'testuser'"))
                    logger.info("Deleted test user")
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