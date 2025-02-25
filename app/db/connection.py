from loguru import logger

import psycopg2
from psycopg2 import pool


class DatabaseConnection:
    _instance = None
    _connection_pool = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_url):
        if not self._connection_pool:
            try:
                self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=db_url
                )
                logger.info("Database connection pool created successfully")
            except Exception as e:
                logger.error(f"Error creating database connection pool: {e}")
                raise

    def get_connection(self):
        try:
            connection = self._connection_pool.getconn()
            logger.debug("Database connection acquired from pool")
            return connection
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            raise

    def release_connection(self, connection):
        try:
            self._connection_pool.putconn(connection)
            logger.debug("Database connection returned to pool")
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            raise

    def close_all_connections(self):
        try:
            self._connection_pool.closeall()
            logger.info("All database connections closed")
        except Exception as e:
            logger.error(f"Error closing all connections: {e}")
            raise
