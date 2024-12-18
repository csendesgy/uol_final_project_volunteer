from django.shortcuts import render

# Create your views here.
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
import base64
import cx_Oracle

def index(request):
    result = None
    images = []

    try:
        # Use cx_Oracle to connect to the database using DSN from settings.py
        dsn = settings.DATABASES['default']['NAME']
        username = settings.DATABASES['default']['USER']
        password = settings.DATABASES['default']['PASSWORD']

        with cx_Oracle.connect(user=username, password=password, dsn=dsn) as connection:
            with connection.cursor() as cursor:

                # Handle image upload if POST request
                if request.method == 'POST' and 'image' in request.FILES:
                    uploaded_image = request.FILES['image'].read()

                    if not uploaded_image:
                        result = "Uploaded image is empty. Please try again."
                    else:
                        # Insert the uploaded image into the database
                        try:
                            cursor.execute(
                                """
                                INSERT INTO UNI_PROJECT.image_tab (uploaded_img, upload_ts)
                                VALUES (:1, SYSTIMESTAMP)
                                """,
                                [uploaded_image]
                            )
                            connection.commit()  # Ensure the transaction is committed
                            print("Insert successful")
                        except Exception as insert_error:
                            print(f"Insert failed: {insert_error}")
                            result = f"Failed to insert image: {insert_error}"
                            raise  # Re-raise the exception for further handling

                        return HttpResponseRedirect(reverse('index'))

                # Query to get the current date from the database
                cursor.execute("SELECT to_char(SYSDATE, 'yyyy-mon-dd hh24:mi:ss') FROM DUAL")
                date_row = cursor.fetchone()
                result = date_row[0] if date_row else "No date returned from database."

                # Fetch all non-null images
                cursor.execute("""
                    SELECT uploaded_img 
                    FROM UNI_PROJECT.image_tab 
                    WHERE uploaded_img IS NOT NULL 
                    ORDER BY upload_ts DESC
                """)
                rows = cursor.fetchall()

                # Check if rows is not empty before processing
                if rows:
                    images = [
                        f"data:image/jpeg;base64,{base64.b64encode(row[0].read()).decode()}"
                        if isinstance(row[0], cx_Oracle.LOB) else f"data:image/jpeg;base64,{base64.b64encode(row[0]).decode()}"
                        for row in rows if row[0] is not None
                    ]

    except cx_Oracle.DatabaseError as e:
        # Log the specific Oracle error
        error, = e.args
        print("Oracle error:", error)
        result = f"Database error: {error.message}"
    except Exception as e:
        # Handle any other exceptions
        print("General error:", str(e))
        result = f"Unexpected error: {str(e)}"

    # Pass the result and images to the template
    return render(request, 'ossvolapp/index.html', {'result': result, 'images': images})
