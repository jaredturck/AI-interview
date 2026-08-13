''' Route custom Django administration, internationalization and candidate API traffic at the project boundary. '''

from django.urls import include, path

from interviews.admin import recruitment_admin_site

urlpatterns = [
    path('admin/', recruitment_admin_site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('api/', include('interviews.urls'))
]
