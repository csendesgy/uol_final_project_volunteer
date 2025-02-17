from django.test.runner import DiscoverRunner
from django.db.backends.oracle.creation import DatabaseCreation

class CustomOracleCreation(DatabaseCreation):
    def _create_test_db(self, verbosity, autoclobber, keepdb=False):
        # Skip the step where Django tries to create the user/schema
        pass

    def _destroy_test_db(self, test_database_name, verbosity):
        # Skip the step where Django tries to drop the user/schema
        pass
    
    def sql_flush(self, style, tables, reset_sequences, allow_cascade=False):
        # Override flush to skip any SQL that would alter your schema.
        # Return an empty list so that no TRUNCATE or DROP statements are run.
        return [
        "TRUNCATE TABLE uni_project_test.event_chat_history",
        "TRUNCATE TABLE uni_project_test.event_chat",
        "TRUNCATE TABLE uni_project_test.recommendations",
        "TRUNCATE TABLE uni_project_test.event_enrollment",
        "TRUNCATE TABLE uni_project_test.event_translate_language",
        "TRUNCATE TABLE uni_project_test.event_skills",
        "TRUNCATE TABLE uni_project_test.events",
        "TRUNCATE TABLE uni_project_test.volunteer_languages",
        "TRUNCATE TABLE uni_project_test.volunteer_skills",
        "TRUNCATE TABLE uni_project_test.profiles_volunteer",
        "TRUNCATE TABLE uni_project_test.profiles_org",
        "TRUNCATE TABLE uni_project_test.skills",
        "TRUNCATE TABLE uni_project_test.languages_level",
        "TRUNCATE TABLE uni_project_test.languages",
        "TRUNCATE TABLE uni_project_test.ossvolapp_authuserextension",
        "TRUNCATE TABLE uni_project_test.auth_user",
        ]   

    def disable_constraint_checking(self):
        # Override constraint checking to do nothing.
        return

    def enable_constraint_checking(self):
        # Override re-enabling constraints to do nothing.
        return
        

class CustomTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        from django.db import connections
        for alias in connections:
            connection = connections[alias]
            if connection.vendor == 'oracle':
                # Force Django to use our custom creation class
                connection.creation = CustomOracleCreation(connection)
        return super().setup_databases(**kwargs)
