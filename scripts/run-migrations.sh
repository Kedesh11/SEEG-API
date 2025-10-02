#!/bin/bash

# Script pour executer les migrations Alembic avant deploiement
set -euo pipefail

# Couleurs
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "========================================"
echo "  EXECUTION DES MIGRATIONS ALEMBIC"
echo "========================================"
echo -e "${NC}"

# Configuration
RESOURCE_GROUP="seeg-backend-rg"
APP_SERVICE_NAME="seeg-backend-api"

# Verifier la connexion Azure
echo -e "${YELLOW}[1/4] Verification de la connexion Azure...${NC}"
if az account show &> /dev/null; then
    ACCOUNT_NAME=$(az account show --query name -o tsv)
    echo -e "      ${GREEN}Connecte a: ${ACCOUNT_NAME}${NC}"
else
    echo -e "      ${RED}ERREUR: Non connecte a Azure${NC}"
    echo -e "      ${YELLOW}Executez: az login${NC}"
    exit 1
fi
echo ""

# Verifier que l'App Service existe
echo -e "${YELLOW}[2/4] Verification de l'App Service...${NC}"
if az webapp show --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}" &> /dev/null; then
    WEBAPP_STATE=$(az webapp show --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}" --query state -o tsv)
    echo -e "      ${GREEN}App Service: ${APP_SERVICE_NAME}${NC}"
    echo -e "      ${GREEN}Status: ${WEBAPP_STATE}${NC}"
else
    echo -e "      ${RED}ERREUR: App Service '${APP_SERVICE_NAME}' introuvable${NC}"
    exit 1
fi
echo ""

# Verifier l'etat actuel des migrations
echo -e "${YELLOW}[3/4] Verification de l'etat actuel des migrations...${NC}"
echo -e "      ${GRAY}Connexion SSH a l'App Service...${NC}"

if CURRENT_MIGRATION=$(az webapp ssh --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}" --command "cd /home/site/wwwroot && alembic current" 2>&1); then
    echo -e "      ${GREEN}Etat actuel des migrations:${NC}"
    echo -e "      ${WHITE}${CURRENT_MIGRATION}${NC}"
else
    echo -e "      ${YELLOW}Impossible de recuperer l'etat (normal si premiere migration)${NC}"
fi
echo ""

# Executer les migrations
echo -e "${YELLOW}[4/4] Execution des migrations...${NC}"
echo -e "      ${GRAY}Commande: alembic upgrade head${NC}"
echo ""

if MIGRATION_OUTPUT=$(az webapp ssh --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}" --command "cd /home/site/wwwroot && alembic upgrade head" 2>&1); then
    echo -e "${CYAN}"
    echo "========================================"
    echo "  MIGRATIONS EXECUTEES AVEC SUCCES"
    echo "========================================"
    echo -e "${NC}"
    
    echo -e "${YELLOW}Sortie des migrations:${NC}"
    echo -e "${WHITE}${MIGRATION_OUTPUT}${NC}"
    echo ""
    
    # Verifier l'etat final
    echo -e "${YELLOW}Verification de l'etat final...${NC}"
    if FINAL_STATE=$(az webapp ssh --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}" --command "cd /home/site/wwwroot && alembic current" 2>&1); then
        echo -e "${GREEN}Etat final: ${FINAL_STATE}${NC}"
    fi
    echo ""
    
    echo -e "${CYAN}Prochaines etapes:${NC}"
    echo -e "  ${WHITE}1. Executer: ./scripts/mise_a_jour.sh (mise a jour application)${NC}"
    echo -e "  ${WHITE}2. Ou executer: ./scripts/deploy-production.sh (deploiement complet)${NC}"
    echo ""
else
    echo -e "${CYAN}"
    echo "========================================"
    echo "  ERREUR LORS DES MIGRATIONS"
    echo "========================================"
    echo -e "${NC}"
    
    echo -e "${RED}Sortie d'erreur:${NC}"
    echo -e "${WHITE}${MIGRATION_OUTPUT}${NC}"
    echo ""
    
    echo -e "${YELLOW}Suggestions:${NC}"
    echo -e "  ${WHITE}1. Verifiez la connexion a la base de donnees${NC}"
    echo -e "  ${WHITE}2. Verifiez les fichiers de migration dans app/db/migrations/versions/${NC}"
    echo -e "  ${WHITE}3. Consultez les logs: az webapp log tail --name ${APP_SERVICE_NAME} --resource-group ${RESOURCE_GROUP}${NC}"
    echo ""
    
    exit 1
fi

echo -e "${CYAN}========================================${NC}"
echo ""

