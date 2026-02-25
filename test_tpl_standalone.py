import os
import django
from django.template.loader import get_template
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_teacher_backend.settings')
django.setup()

try:
    get_template('core/account.html')
    print("Template parsed OK")
except Exception as e:
    traceback.print_exc()
