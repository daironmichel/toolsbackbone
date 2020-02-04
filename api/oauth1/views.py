from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from trader.models import ServiceProvider
from trader.providers import get_provider_instance


@api_view(['POST'])
def oauth1_verify(request: Request):
    data = request.data
    oauth_token = data.get("oauthToken", None)
    oauth_verifier = data.get("oauthVerifier", None)

    if not oauth_token:
        return Response({
            "error": f'oauthToken required'
        })

    provider = ServiceProvider.objects \
        .filter(session__request_token=oauth_token) \
        .select_related('session', 'broker', 'user__auth_token') \
        .first()

    if not provider:
        return Response({
            "error": f'no session found for provided oauthToken'
        })

    etrade = get_provider_instance(provider)
    try:
        provider = etrade.authorize(oauth_verifier)
    except KeyError as e:
        if f'Token {oauth_token} is invalid, or has expired' in str(e):
            return Response({
                "error": f'Token expired.'
            })
        else:
            raise

    return Response({
        "accessToken": provider.user.auth_token.key,
        "brokerSlug": provider.broker.slug,
        "providerSlug": provider.slug,
    })
