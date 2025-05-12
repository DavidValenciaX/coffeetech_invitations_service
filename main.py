from fastapi import FastAPI
from endpoints import invitations, invitations_service
from utils.logger import setup_logger

# Setup logging for the entire application
logger = setup_logger()
logger.info("Starting CoffeeTech Invitations Service")

app = FastAPI()

# Incluir las rutas de invitaciones
app.include_router(invitations.router, prefix="/invitations", tags=["Invitaciones"])

# Incluir las rutas del servicio de invitacionespara que se conecten otros servicios
app.include_router(invitations_service.router, prefix="/invitations-service", include_in_schema=False)

@app.get("/", include_in_schema=False)
def read_root():
    """
    Ruta raíz que retorna un mensaje de bienvenida.

    Returns:
        dict: Un diccionario con un mensaje de bienvenida.
    """
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the FastAPI application CoffeeTech Invitations Service!"}