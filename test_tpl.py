from django.template.loader import get_template
import traceback

try:
    get_template('core/account.html')
    print('Template parsed OK')
except Exception as e:
    traceback.print_exc()
