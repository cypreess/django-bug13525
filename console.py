from django.utils.regex_helper import normalize
from django.conf import settings
settings.configure()


print(normalize('dupa(blada)'))