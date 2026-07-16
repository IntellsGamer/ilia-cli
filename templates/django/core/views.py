from django.http import JsonResponse

def index(request):
    return JsonResponse({
        "project": "{{ project_name }}",
        "version": "{{ version }}",
        "message": "Hello from Django!"
    })
