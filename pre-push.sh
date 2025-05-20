#!/bin/bash
# Script de vérification avant push
# Placer ce fichier dans .git/hooks/pre-push et le rendre exécutable avec: chmod +x .git/hooks/pre-push

echo "=== Vérification du backend avant push ==="

# Vérifier que le serveur est en cours d'exécution
if ! curl -s http://localhost:8001/docs > /dev/null; then
    echo " ERREUR: Le serveur backend n'est pas en cours d'exécution"
    echo "Démarrer le serveur avec: uvicorn app.main:app --reload --port 8001"
    exit 1
fi

# Exécuter les vérifications de santé
echo "Exécution des vérifications de santé..."
python health_check.py
if [ $? -ne 0 ]; then
    echo " Les vérifications de santé ont échoué. Push annulé."
    exit 1
fi

# Exécuter les tests des endpoints
echo "Exécution des tests des endpoints..."
python test_all_endpoints_extended.py
if [ $? -ne 0 ]; then
    echo " Les tests des endpoints ont échoué. Push annulé."
    exit 1
fi

# Exécuter les tests de génération de sommaire
echo "Exécution des tests de génération de sommaire..."
# Exu00e9cuter les tests de gu00e9nu00e9ration de sommaire
echo "Exu00e9cution des tests de gu00e9nu00e9ration de sommaire..."
python test_summary_generation.py
if [ $? -ne 0 ]; then
    echo "u274c Les tests de gu00e9nu00e9ration de sommaire ont u00e9chouu00e9. Push annulu00e9."
    exit 1
fi

echo "u2705 Toutes les vu00e9rifications ont ru00e9ussi. Push autorisu00e9."
exit 0
