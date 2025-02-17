from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import connection
import traceback  # Useful for debugging


class EventAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        try:
            with connection.cursor() as cursor:
                # Use a properly formatted query with Oracle-style placeholders
                query = """
                    WITH aggregated_data AS (
                        SELECT
                            e.event_name,
                            e.event_zip,
                            e.event_date,
                            e.event_description,
                            e.application_deadline,
                            o.org_name,
                            LISTAGG(DISTINCT sk.skill_name, '; ') WITHIN GROUP (ORDER BY sk.skill_name) AS skills,
                            LISTAGG(DISTINCT l.language || ' - ' || ll.languages_level, '; ') WITHIN GROUP (ORDER BY l.language) AS languages,
                            e.event_id,
                            COUNT(DISTINCT CASE WHEN er.is_accepted = 'Y' THEN er.profiles_vol_id END) AS no_of_attendees
                        FROM events e
                        JOIN profiles_org o ON e.profiles_org_id = o.profiles_org_id
                        LEFT JOIN event_skills es ON e.event_id = es.event_id
                        LEFT JOIN skills sk ON es.skill_id = sk.skill_id
                        LEFT JOIN event_translate_language el ON e.event_id = el.event_id
                        LEFT JOIN languages l ON el.target_language_id = l.language_id
                        LEFT JOIN languages_level ll ON el.required_language_level_id = ll.languages_level_id
                        LEFT JOIN event_enrollment er ON (e.event_id = er.event_id AND er.is_accepted = 'Y')
                        WHERE e.event_id = :event_id
                        GROUP BY
                            e.event_name,
                            e.event_zip,
                            e.event_date,
                            e.event_description,
                            e.application_deadline,
                            o.org_name,
                            e.event_id
                    )
                    SELECT
                        ad.event_name,
                        ad.event_zip,
                        ad.event_date,
                        ad.event_description,
                        ad.application_deadline,
                        --e.event_image,
                        ad.org_name,
                        ad.skills,
                        CASE
                            WHEN ad.languages = ' - ' THEN NULL
                            ELSE ad.languages
                        END AS languages,
                        ad.no_of_attendees
                    FROM aggregated_data ad
                    --JOIN events e ON ad.event_id = e.event_id
                """
                cursor.execute(query, {'event_id': event_id})
                row = cursor.fetchone()
                if row:
                    # Split skills and languages into lists
                    skills = row[6].split('; ') if row[6] else []
                    languages = row[7].split('; ') if row[7] else []

                    event_data = {
                        'event_name': row[0],
                        'event_zip': row[1],
                        'event_date': row[2],
                        'event_description': row[3],
                        'application_deadline': row[4],
                        'organizer_name': row[5],
                        'skills': skills,
                        'languages': languages,
                        'attendees': row[8] or 0,
                    }
                    return Response(event_data, status=200)
                return Response({"error": "Event not found."}, status=404)
        except Exception as e:
            traceback.print_exc()  # Log traceback for debugging
            return Response({"error": "An error occurred while fetching event details."}, status=500)
