from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from ..core.security import get_current_user
from ..models.client import ClientCreate, ClientUpdate
from ..db.client_queries import create_client, get_client, get_clients, update_client, delete_client

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.post("/", response_model=dict)
async def create_client_route(
    client_data: ClientCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Cru00e9e un nouveau client.
    
    - **name**: Nom du client
    - **summary_template**: Template personnalisu00e9 pour les comptes rendus (optionnel)
    
    Retourne les informations du client cru00e9u00e9.
    """
    client = create_client(client_data.dict(), current_user["id"])
    if not client:
        raise HTTPException(status_code=500, detail="Erreur lors de la cru00e9ation du client")
    return client

@router.get("/", response_model=List[dict])
async def list_clients(
    current_user: dict = Depends(get_current_user)
):
    """
    Liste tous les clients de l'utilisateur.
    
    Retourne la liste des clients avec leurs informations.
    """
    return get_clients(current_user["id"])

@router.get("/{client_id}", response_model=dict)
async def get_client_route(
    client_id: str = Path(..., description="ID unique du client"),
    current_user: dict = Depends(get_current_user)
):
    """
    Ru00e9cupu00e8re les informations d'un client spu00e9cifique.
    
    - **client_id**: Identifiant unique du client
    
    Retourne les informations du client.
    """
    client = get_client(client_id, current_user["id"])
    if not client:
        raise HTTPException(
            status_code=404, 
            detail={
                "message": "Client non trouvé",
                "client_id": client_id,
                "type": "CLIENT_NOT_FOUND"
            }
        )
    return client

@router.put("/{client_id}", response_model=dict)
async def update_client_route(
    client_id: str = Path(..., description="ID unique du client"),
    client_update: ClientUpdate = ...,
    current_user: dict = Depends(get_current_user)
):
    """
    Met u00e0 jour les informations d'un client.
    
    - **client_id**: Identifiant unique du client
    - **client_update**: Donnu00e9es u00e0 mettre u00e0 jour
    
    Retourne les informations du client mises u00e0 jour.
    """
    # Filtrer les valeurs non nulles pour la mise u00e0 jour
    update_data = {k: v for k, v in client_update.dict(exclude_unset=True).items() if v is not None}
    client = update_client(client_id, current_user["id"], update_data)
    
    if not client:
        raise HTTPException(
            status_code=404, 
            detail={
                "message": "Client non trouvé",
                "client_id": client_id,
                "type": "CLIENT_NOT_FOUND"
            }
        )
    
    return client

@router.delete("/{client_id}", response_model=dict)
async def delete_client_route(
    client_id: str = Path(..., description="ID unique du client"),
    current_user: dict = Depends(get_current_user)
):
    """
    Supprime un client.
    
    - **client_id**: Identifiant unique du client
    
    Cette opu00e9ration supprime le client de la base de donnu00e9es mais ne modifie pas les ru00e9unions existantes.
    """
    success = delete_client(client_id, current_user["id"])
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail={
                "message": "Client non trouvé",
                "client_id": client_id,
                "type": "CLIENT_NOT_FOUND"
            }
        )
    
    return {"message": "Client supprimu00e9 avec succu00e8s"}
