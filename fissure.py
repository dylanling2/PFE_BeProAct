import cv2
import numpy as np
import random

# Charger l'image
image_path = "bitume.jpg"  # Remplacez par votre chemin d'image
image = cv2.imread(image_path)

# Vérifier si l'image a été correctement chargée
if image is None:
    print("Erreur : Impossible de charger l'image. Vérifiez le chemin.")
    exit()

# Convertir l'image en niveaux de gris
gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Calculer la luminosité moyenne
average_brightness = np.mean(gray_image)
print(f"Luminosité moyenne : {average_brightness}")

# Ajuster dynamiquement le seuil basé sur la luminosité moyenne
# Vous pouvez ajuster le facteur d'ajustement selon les besoins
threshold_value = int(average_brightness * 0.7)
print(f"Valeur de seuillage ajustée : {threshold_value}")

# Appliquer un flou pour réduire le bruit
blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)

# Appliquer un seuillage global pour détecter les défauts sombres
_, binary_image = cv2.threshold(blurred_image, threshold_value, 255, cv2.THRESH_BINARY_INV)

# Trouver les contours
contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Créer un masque vide pour fusionner les contours
mask = np.zeros_like(binary_image)

# Dessiner tous les contours sur le masque
min_contour_area = 3000  # Seuil de filtrage des contours
for contour in contours:
    if cv2.contourArea(contour) > min_contour_area:
        cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)

# Trouver les contours fusionnés sur le masque
merged_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Copier l'image originale pour dessiner les contours fusionnés
output_image = image.copy()

# Appliquer une couleur aléatoire à chaque défaut détecté, calculer ses dimensions, le numéroter, et le classifier
for i, contour in enumerate(merged_contours):
    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    cv2.drawContours(output_image, [contour], -1, color, 2)

    # Calculer la boîte englobante du contour
    x, y, w, h = cv2.boundingRect(contour)

    # Tracer un rectangle autour du défaut
    cv2.rectangle(output_image, (x, y), (x + w, y + h), color, 2)

    # Calculer la longueur et la largeur
    length = max(w, h)
    width = min(w, h)

    # Calculer l'aspect ratio
    aspect_ratio = length / width

    # Classifier le défaut
    defect_type = "Fissure" if aspect_ratio > 3 else "Trou"

    # Afficher le numéro du défaut, la longueur, la largeur, et le type de défaut sur l'image
    dimensions_text = f"Defaut {i}: L: {length}px, W: {width}px, {defect_type}"
    cv2.putText(output_image, dimensions_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Imprimer les informations dans la console
    print(f"Defaut {i}: Longueur: {length}px, Largeur: {width}px, Type: {defect_type}")

# Afficher le nombre total de défauts détectés
print(f"Nombre total de défauts détectés: {len(merged_contours)}")

# Afficher l'image originale et l'image avec les contours fusionnés détectés
cv2.imshow("Image Originale", image)
cv2.imshow("Contours Fusionnes Detectes", output_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
