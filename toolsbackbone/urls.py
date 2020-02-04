"""toolsbackbone URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from rest_auth.views import LoginView, LogoutView

from api.graphql.views import PrivateGraphQLView, TokenAuthGraphQLView
from api.oauth1.views import oauth1_verify
from api.views import credentials

urlpatterns = [
    path('api/login/', LoginView.as_view(), name='rest_login'),
    # URLs that require a user to be logged in with a valid session / token.
    path('api/logout/', LogoutView.as_view(), name='rest_logout'),
    path('api/credentials/', credentials, name='rest_credentials'),
    path('api/oauth1/verify/', oauth1_verify, name='oauth1_verify'),
    path('api/gql/', TokenAuthGraphQLView.as_view(graphiql=False)),
    path('graphiql/', PrivateGraphQLView.as_view(graphiql=True)),
    # django admin
    path('', admin.site.urls),
]
