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
                    WITH list_1 as (
                      SELECT 
                          e.event_name,
                          e.event_zip,
                          e.event_date,
                          e.event_description,
                          e.application_deadline,
                          o.org_name,
                          LISTAGG(sk.skill_name, '; ') WITHIN GROUP (ORDER BY sk.skill_name) AS skills,
                          e.event_id
                      FROM uni_project.events e
                      JOIN profiles_org o ON e.profiles_org_id = o.profiles_org_id
                      LEFT JOIN uni_project.event_skills es ON e.event_id = es.event_id
                      LEFT JOIN uni_project.skills sk ON es.skill_id = sk.skill_id
                      WHERE e.event_id = :event_id
                      GROUP BY 
                          e.event_name, e.event_zip, e.event_date, e.event_description, 
                          e.application_deadline
                          , o.org_name, e.event_id
                      )
                    , list_2 as ( 
                    select 
                    l1.event_name,
                        l1.event_zip,
                        l1.event_date,
                        l1.event_description,
                        l1.application_deadline,
                        l1.org_name,
                        l1.skills,
                        l1.event_id
                        , LISTAGG(l.language || ' - ' || ll.languages_level, '; ') WITHIN GROUP (ORDER BY l.language) AS languages
                     from list_1 l1
                    LEFT JOIN uni_project.event_translate_language el ON l1.event_id = el.event_id
                    LEFT JOIN uni_project.languages l ON el.target_language_id = l.language_id
                    LEFT JOIN uni_project.languages_level ll ON el.required_language_level_id = ll.languages_level_id
                    group by l1.event_name, l1.event_zip, l1.event_date,
                        l1.event_description, l1.application_deadline,
                        l1.org_name, l1.skills, l1.event_id)                  
                    , list_3 as (
                    select l2.event_name,
                        l2.event_zip,
                        l2.event_date,
                        l2.event_description,
                        l2.application_deadline,
                    --    e2.event_image,
                        l2.org_name,
                        l2.skills,
                        case 
                          when l2.languages = ' - ' then null
                        else l2.languages end languages,
                        l2.event_id, 
                        count(er.event_id) as no_of_attendees
                    from list_2 l2
                    left join uni_project.event_enrollment er on (l2.event_id = er.event_id  and er.is_accepted = 'Y')
                    group by l2.event_name,
                        l2.event_zip,
                        l2.event_date,
                        l2.event_description,
                        l2.application_deadline,
                        l2.org_name,
                        l2.skills,
                        case 
                          when l2.languages = ' - ' then null
                        else l2.languages end,
                        l2.event_id
                          )
                    Select l3.event_name,
                        l3.event_zip,
                        l3.event_date,
                        l3.event_description,
                        l3.application_deadline,
                        --e2.event_image,
                        l3.org_name,
                        l3.skills,
                        l3.languages,
                        l3.no_of_attendees
                    from list_3 l3
                    join uni_project.events e2 on l3.event_id = e2.event_id
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
