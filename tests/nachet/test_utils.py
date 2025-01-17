import os
import unittest

class EnvironmentVariableError(Exception):
    pass

class Test_Utils(unittest.TestCase):
    
    def test_secrets(self):
        NACHET_SCHEMA = os.getenv("NACHET_SCHEMA")
        if not NACHET_SCHEMA:
            raise EnvironmentVariableError("NACHET_SCHEMA is not set")
        
        NACHET_DB_URL = os.getenv("NACHET_DB_URL")
        if not NACHET_DB_URL:
            raise EnvironmentVariableError("NACHET_DB_URL is not set")
        NACHET_DB_USER = os.getenv("NACHET_DB_USER")
        if not NACHET_DB_USER:
            raise EnvironmentVariableError("NACHET_DB_USER is not set")
        NACHET_DB_PASSWORD = os.getenv("NACHET_DB_PASSWORD")
        if not NACHET_DB_PASSWORD:
            raise EnvironmentVariableError("NACHET_DB_PASSWORD is not set")
