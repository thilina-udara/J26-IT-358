"""Account endpoints; existing research roles stay outside the account registry."""
from fastapi import APIRouter, Depends, Request, Response
from app.schemas.auth import RegisterInput, LoginInput, FarmerIdentity, SessionResponse
from app.services.farmer_auth import unauthorized
from app.schemas.api_responses import error_responses


def router(auth_store, farmer_profile, security, roles):
    routes = APIRouter(prefix='/auth', tags=['farmer accounts'])

    def client_attempt(request, repository):
        # Do not trust X-Forwarded-For here; configure trusted proxies at deployment.
        address = request.client.host if request.client else 'unknown'
        repository.reserve_attempt('client', address, 40)

    @routes.post('/register', response_model=FarmerIdentity, status_code=201,
                 responses=error_responses(409,422,429,503))
    def register(value: RegisterInput, request: Request, repository=Depends(auth_store)):
        farmers, _, _ = roles()
        client_attempt(request, repository)
        return repository.register(value, set(farmers.values()))

    @routes.post('/login', response_model=SessionResponse,responses=error_responses(401,422,429,503))
    def login(value: LoginInput, request: Request, repository=Depends(auth_store)):
        roles()  # Invalid/ambiguous role configuration must continue to fail closed.
        client_attempt(request, repository)
        return repository.login(value)

    @routes.get('/me', response_model=FarmerIdentity,responses=error_responses(401,503))
    def me(profile=Depends(farmer_profile)):
        return profile

    @routes.post('/logout', status_code=204,responses=error_responses(401,503))
    def logout(credentials=Depends(security), repository=Depends(auth_store)):
        roles()
        if credentials is None:
            raise unauthorized()
        # Static research credentials cannot be revoked by a persisted session endpoint.
        repository.logout(credentials.credentials)
        return Response(status_code=204)

    return routes
