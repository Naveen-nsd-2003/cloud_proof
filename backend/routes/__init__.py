""" # backend/routes/__init__.py


from fastapi import APIRouter
from .users import router as users_router
from .gigs import router as gigs_router
from .invoices import router as invoices_router

# Create a main router that combines all individual routers
api_router = APIRouter()

api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(gigs_router, prefix="/gigs", tags=["Gigs"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])
 """

# backend/routes/__init__.py

from .users import users_bp
from .gigs import gigs_bp
from .invoices import invoices_bp
