import cv2
import numpy as np
import random

# Chemin de la vidéo
video_path = "video2.mp4"  # Remplacez par votre chemin de fichier vidéo

# Ouvrir la vidéo
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Erreur : Impossible de lire la vidéo. Vérifiez le chemin.")
    exit()

# Dictionnaire pour stocker les défauts détectés et leur compteur de frames
defects_memory = {}
min_frames_persistence = 10  # Nombre minimum de frames pour considérer un défaut

frame_index = 0

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    # Convertir l'image en niveaux de gris
    gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Calculer la luminosité moyenne
    average_brightness = np.mean(gray_image)

    # Ajuster dynamiquement le seuil basé sur la luminosité moyenne
    threshold_value = int(average_brightness * 0.7)

    # Appliquer un flou pour réduire le bruit (réduction légère pour capturer les petits détails)
    blurred_image = cv2.GaussianBlur(gray_image, (3, 3), 0)

    # Appliquer un seuillage global pour détecter les défauts sombres
    _, binary_image = cv2.threshold(blurred_image, threshold_value, 255, cv2.THRESH_BINARY_INV)

    # Trouver les contours
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Créer un masque vide pour fusionner les contours
    mask = np.zeros_like(binary_image)

    # Dessiner tous les contours sur le masque
    min_contour_area = 500  # Réduction du seuil de filtrage des contours pour détecter de petites fissures
    for contour in contours:
        if cv2.contourArea(contour) > min_contour_area:
            cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)

    # Trouver les contours fusionnés sur le masque
    merged_contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Copier l'image originale pour dessiner les contours fusionnés
    output_frame = frame.copy()

    # Mémoriser les défauts présents dans cette frame
    current_defects = {}

    for i, contour in enumerate(merged_contours):
        # Calculer la boîte englobante du contour
        x, y, w, h = cv2.boundingRect(contour)
        defect_id = (x, y, w, h)

        # Stocker ou mettre à jour le compteur de frames du défaut
        if defect_id in defects_memory:
            defects_memory[defect_id] += 1
        else:
            defects_memory[defect_id] = 1

        # Ajouter au dictionnaire des défauts actuels
        current_defects[defect_id] = defects_memory[defect_id]

        # Tracer un rectangle autour du défaut
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        cv2.rectangle(output_frame, (x, y), (x + w, y + h), color, 2)

        # Convertir les dimensions en centimètres
        length_cm = max(w, h) / 10.0
        width_cm = min(w, h) / 10.0

        # Calculer l'aspect ratio
        aspect_ratio = length_cm / width_cm

        # Classifier le défaut
        defect_type = "Fissure" if aspect_ratio > 3 else "Trou"

        # Afficher les dimensions et le type du défaut
        dimensions_text = f"Defaut: L: {length_cm:.2f}cm, W: {width_cm:.2f}cm, {defect_type}"
        cv2.putText(output_frame, dimensions_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Filtrer et conserver les défauts qui persistent au moins un certain nombre de frames
    defects_memory = {k: v for k, v in defects_memory.items() if v >= min_frames_persistence}

    # Afficher la frame avec les défauts persistants
    cv2.imshow("Defauts Detectes", output_frame)

    # Quitter la boucle si 'q' est pressé
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    frame_index += 1

# Libérer les ressources
cap.release()
cv2.destroyAllWindows()
